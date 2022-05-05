import asyncio
import aiohttp
import base64
import json
from typing import Optional

from io import BytesIO
from PIL import Image, ImageOps

from .skin_render import Render


async def get_players_by_name(names: list, session: aiohttp.ClientSession = None):
    """Useful helper function to get multiple :class:`Player` objects

    Only does one API call for the entire list instead of one per player
    This is recommended to be used if you have a list of usernames

    Parameters
    ----------
    names: list
        A list of minecraft usernames
    session: aiohttp.ClientSession
        Alternative ClientSession for the request

    Returns
    -------
    list
        A list of :class:`Player` objects

    Raises
    ------
    ValueError
        An empty list was passed
    """
    if not names:
        raise ValueError("Pass at least one minecraft username")

    if session is None:
        session = aiohttp.ClientSession()
        close = True
    else:
        close = False

    players = []
    async with session.post("https://api.mojang.com/profiles/minecraft", json=names) as resp:
        if resp.status == 200:
            for entry in await resp.json():
                players.append(Player(uuid=entry["id"], session=session if not close else None))

    if close:
        await session.close()

    return players


class Player:
    """Class representing a minecraft player
    This has to be created before a skin can be rendered

    Parameters
    ----------
    uuid: str
        UUID of the player (Not needed if name is given
    name: str
        Username of the player (Not needed if UUID is given)
    raw_skin: Image.Image
        Raw skin image of the player (64x64px)
    raw_cape: Image.Image
        Raw cape image of the player (64x64px)
    session: aiohttp.ClientSession
        ClientSession to use for requests
    """
    def __init__(
            self,
            uuid: str = None,
            name: str = None,
            raw_skin: Image.Image = None,
            raw_cape: Image.Image = None,
            session: aiohttp.ClientSession = None
    ):
        self._uuid: Optional[str] = uuid
        self._username: Optional[str] = name
        self._slim: Optional[bool] = None

        self._skin: Optional[Image.Image] = None
        self._head: Optional[Image.Image] = None
        self._raw_skin: Optional[Image.Image] = raw_skin
        self._raw_cape: Optional[Image.Image] = raw_cape
        self._raw_skin_url: Optional[str] = None
        self._raw_cape_url: Optional[str] = None

        self._session: Optional[aiohttp.ClientSession] = session
        self._close_session: bool = False

        self._ready: asyncio.Event = asyncio.Event()
        if self._uuid:
            self._uuid = self._uuid.replace("-", "") #convert to universal uuid format

            if len(self._uuid) != 32:
                raise ValueError("UUID seems to be invalid.")

    def __repr__(self):
        return f"<Player (UUID={self.uuid}) (name={self.name}) (slim={self.is_slim})>"

    @property
    def uuid(self):
        """The players UUID"""
        return self._uuid

    @property
    def name(self):
        """The players name"""
        return self._username

    @property
    def skin(self):
        """The last rendered full skin"""
        return self._skin

    @property
    def head(self):
        """The last rendered head"""
        return self._head

    @property
    def raw_skin(self):
        """Raw skin image returned from the mojang api"""
        return self._raw_skin

    @property
    def raw_skin_url(self):
        """Raw skin url to query the skin from the mojang api"""
        return self._raw_skin_url

    @property
    def raw_cape(self):
        """Raw cape image returned from the mojang api"""
        return self._raw_cape

    @property
    def raw_cape_url(self):
        """Raw cape url to query the cape from the mojang api"""
        return self._raw_cape_url

    @property
    def has_cape(self):
        """Whether the player has  a cape"""
        return bool(self._raw_cape_url)

    @property
    def is_slim(self):
        """Whether the players skin is slim or classic"""
        return self._slim

    async def initialize(self):
        """Initializes the player class

        This function fetches skin and cape from the mojang API and caches them
        Once this function has finished, renders of the skin can be created

        Warning
        -------
        This function does two to four API calls to the mojang API:
            -> (1.) Obtain the players UUID by name (Only if no UUID is given)\n
            -> 2. Get the players profile\n
            -> 3. Get the players skin\n
            -> (4.) Get the players cape (Only if the player actually has a cape)\n
        Rate limits of the API are unknown but expected to be somewhere close to 6000 requests per 10 minutes.
        """
        if self._uuid is None and self._username is None:
            raise ValueError

        if not self._session:
            self._session = aiohttp.ClientSession()
            self._close_session = True

        if self._uuid is None:
            async with self._session.get(
                f"https://api.mojang.com/users/profiles/minecraft/{self._username}"
            ) as resp:
                if resp.status == 200:
                    resp_dict = await resp.json()
                    self._uuid = resp_dict["uuid"].replace("-", "")

        if self._uuid is not None:
            async with self._session.get(
                f"https://sessionserver.mojang.com/session/minecraft/profile/{self._uuid}"
            ) as resp:
                if resp.status == 200:
                    resp_dict = await resp.json()

                    self._username = resp_dict["name"] if self._username is None else self._username

                    for p in resp_dict["properties"]:
                        if p["name"] == "textures":
                            textures = json.loads(base64.b64decode(p["value"]))["textures"]
                            break

                    else:
                        raise NotImplementedError

        self._raw_skin_url = textures["SKIN"]["url"]
        self._raw_cape_url = textures["CAPE"]["url"] if "CAPE" in textures.keys() else None

        if textures:
            if not self._raw_skin:
                try:
                    self._slim = True if textures["SKIN"]["metadata"]["model"] == "slim" else False
                except KeyError:
                    self._slim = False

                async with self._session.get(self._raw_skin_url) as resp:
                    self._raw_skin = Image.open(BytesIO(await resp.read()))

            if not self._raw_cape:
                if self._raw_cape_url is not None:
                    async with self._session.get(self._raw_cape_url) as resp:
                        self._raw_cape = Image.open(BytesIO(await resp.read()))

        if self._raw_skin.height == 32: #old skin format
            new_skin_im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            new_skin_im.paste(self._raw_skin, 0, 0)

            for i in range(2):
                f1 = 40 if i != 0 else 0
                f2 = 16 if i != 0 else 0

                new_skin_im.paste(ImageOps.mirror(self._raw_skin.crop((4+f1, 16, 8+f1, 20))), (20+f2, 48))
                new_skin_im.paste(ImageOps.mirror(self._raw_skin.crop((8+f1, 16, 12+f1, 20))), (24+f2, 48))
                new_skin_im.paste(ImageOps.mirror(self._raw_skin.crop((8+f1, 20, 12+f1, 32))), (16+f2, 52))
                new_skin_im.paste(ImageOps.mirror(self._raw_skin.crop((12+f1, 20, 16+f1, 32))), (20+f2, 52))
                new_skin_im.paste(ImageOps.mirror(self._raw_skin.crop((4+f1, 20, 8+f1, 32))), (24+f2, 52))
                new_skin_im.paste(ImageOps.mirror(self._raw_skin.crop((0+f1, 20, 4+f1, 32))), (28+f2, 52))

            self._raw_skin = new_skin_im

        #slim skin detection for passed skins
        if self._slim is None: #skin has been passed
            if self._raw_skin.getpixel((46, 52))[3] == 0:
                self._slim = True
            else:
                self._slim = False

        if self._close_session:
            await self._session.close()

        self._ready.set()

    async def wait_for_fully_constructed(self):
        """Returns as soon as the initialize function finished

        Waiting for this guarantees that the skin has been fetched from the api"""
        try:
            await asyncio.wait_for(self._ready.wait(), timeout=60)
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError

    async def render_skin(
            self,
            vr: int = 25,
            hr: int = 35,
            hrh: int = 0,
            vrll: int = 0,
            vrrl: int = 0,
            vrla: int = 0,
            vrra: int = 0,
            ratio: int = 12,
            display_hair: bool = True,
            display_second_layer: bool = True,
            display_cape: bool = True,
            aa: bool = False,
    ) -> Optional[Image.Image]:
        """Render a full body skin

        Parameters
        ----------
        vr: int
            Vertical rotation of the output image
        hr: int
            Horizontal rotation of the output image
        hrh: int
            Horizontal head rotation
        vrll: int
            Vertical rotation of the left leg
        vrrl: int
            Vertical rotation of the right leg
        vrla: int
            Vertical rotation of the left arm
        vrra: int
            Vertical rotation of the right arm
        ratio: int
            Resolution of the returned image
        display_hair: bool
            Whether or not the second head layer is displayed
        display_second_layer: bool
            Whether or not the second skin layer is displayed
        display_cape: bool
            Whether or not the player's cape is shown
        aa: bool
            Antializing: smoothens the corners a bit

        Returns
        -------
        PIL.Image.Image
            The rendered skin
        """
        await self.wait_for_fully_constructed()
        render = Render(
            player=self,
            vr=vr,
            hr=hr,
            hrh=hrh,
            vrll=vrll,
            vrrl=vrrl,
            vrla=vrla,
            vrra=vrra,
            vrc=0,
            ratio=ratio,
            head_only=False,
            display_hair=display_hair,
            display_layers=display_second_layer,
            display_cape=display_cape,
            aa=aa,
        )
        im = await render.get_render()
        self._skin = im
        return im

    async def render_head(
            self,
            vr: int = 25,
            hr: int = 35,
            ratio: int = 12,
            display_hair: bool = True,
            aa: bool = False,
    ) -> Optional[Image.Image]:
        """Render the players head

        Parameters
        ----------
        vr: int
            Vertical rotation of the output image
        hr: int
            Horizontal rotation of the output image
        ratio: int
            Resolution of the returned image
        display_hair: bool
            Whether or not the second head layer should be displayed
        aa: bool
            Antializing: smoothens the corners a bit

        Returns
        -------
        PIL.Image.Image
            The rendered head
        """
        await self.wait_for_fully_constructed()
        render = Render(
            player=self,
            vr=vr,
            hr=hr,
            ratio=ratio,
            head_only=True,
            display_hair=display_hair,
            aa=aa,
        )
        im = await render.get_render()
        self._head = im
        return im
