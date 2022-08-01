import asyncio
import base64
import json
from io import BytesIO
from typing import Optional

import aiohttp
from PIL import Image, ImageOps

from .skin_render import Render
from .utils import (
    fetch_optifine_cape,
    fetch_labymod_cape,
    fetch_5zig_cape,
    fetch_minecraftcapes_cape,
    name_to_uuid,
    uuid_to_undashed,
)


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
        Raw cape image of the player (64x32px)
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

        self._skin: Optional[Skin] = None
        self._raw_skin: Optional[Image.Image] = raw_skin
        self._raw_capes: dict = {
            "default": raw_cape,
            "mojang": None,
            "optifine": None,
            "labymod": None,
            "5zig": None,
            "minecraftcapes": None,
        }

        self._session: Optional[aiohttp.ClientSession] = session
        self._close_session: bool = False

        self._ready: asyncio.Event = asyncio.Event()
        if self._uuid:
            self._uuid = uuid_to_undashed(self._uuid)

            if len(self._uuid) != 32:
                raise ValueError("UUID seems to be invalid.")

    def __repr__(self):
        return f"<Player (UUID={self.uuid}) (name={self.name}) (skin={self._skin})>"

    @property
    def uuid(self):
        """The players UUID\n
        Either passed when creating this class or fetched from the MojangAPI"""
        return self._uuid

    @property
    def name(self):
        """The players name"""
        return self._username

    @property
    def skin(self):
        """The players :class:`Skin`"""
        return self._skin

    @property
    def capes(self):
        """A dict representing this player's capes"""
        return self._raw_capes

    @property
    def mojang_cape(self):
        """The player's mojang cape"""
        return self._raw_capes["mojang"]

    @property
    def optifine_cape(self):
        """The player's optifine cape"""
        return self._raw_capes["optifine"]

    @property
    def labymod_case(self):
        """The player's labymod cape"""
        return self._raw_capes["labymod"]

    @property
    def minecraftcapes_cape(self):
        """The player's MinecraftCapes cape"""
        return self._raw_capes["minecraftcapes"]

    @property
    def zig_cape(self):
        """The player's 5Zig cape"""
        return self._raw_capes["5zig"]

    def set_skin(self, skin: "Skin"):
        """Manually overwrite/set this players skin

        Parameters
        ----------
        skin: Skin
            The new skin
        """
        self._skin = skin

    async def initialize(self):
        """Initializes the player class

        This function is an initializer which helps to get various details about the player with just one method.
        Once this function has finished running, the corresponding :py:class:`Player` object is
        guaranteed to have a name, UUID and skin (includes the cape if available) associated to it
        (if the given username and/or UUID is valid of course).

        Warning
        -------
        This function does one to four API calls to the mojang API:
            -> (1.) Obtain the players UUID by name (Only if no UUID is given)\n
            -> 2. Get the players profile\n
            -> (3.) Get the players skin (Only if no skin is given)\n
            -> (4.) Get the players cape (Only if the player actually has a cape)\n
        Rate limits of the API are unknown but expected to be somewhere close to 6000 requests per 10 minutes.
        """
        if self._uuid is None and self._username is None:
            raise ValueError

        if not self._session:
            self._session = aiohttp.ClientSession()
            self._close_session = True

        if self._uuid is None:
            uuid = await name_to_uuid(self._username, self._session)
            if uuid:
                self._uuid = uuid_to_undashed(uuid)

        if self._uuid is not None and (self._raw_skin is None or self._raw_capes["default"] is None):
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

        if textures:
            _raw_skin_url = textures["SKIN"]["url"]
            _raw_cape_url = textures["CAPE"]["url"] if "CAPE" in textures.keys() else None

            if not self._raw_skin:
                async with self._session.get(_raw_skin_url) as resp:
                    self._raw_skin = Image.open(BytesIO(await resp.read()))

            if not self._raw_capes["default"]:
                if _raw_cape_url is not None:
                    async with self._session.get(_raw_cape_url) as resp:
                        self._raw_capes["default"] = Image.open(BytesIO(await resp.read()))
                        self._raw_capes["mojang"] = self._raw_capes["default"]
                else:
                    self._raw_capes["default"] = None

            self._skin = Skin(
                raw_skin=self._raw_skin,
                raw_skin_url=_raw_skin_url,
                raw_cape=self._raw_capes["default"],
                raw_cape_url=_raw_cape_url
            )

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

    async def fetch_optifine_cape(self):
        """Fetch this players optifine cape and stores it to :py:attr:`Player.optifine_cape`
        
        This is basically just an alias for :py:func:`utils.fetch_optifine_cape`"""
        cape = await fetch_optifine_cape(self)
        if cape:
            self._raw_capes["optifine"] = cape

    async def fetch_labymod_cape(self):
        """Fetch this players labymod cape and stores it to :py:attr:`Player.labymod_cape`

        This is basically just an alias for :py:func:`utils.fetch_labymod_cape`"""
        cape = await fetch_labymod_cape(self)
        if cape:
            self._raw_capes["labymod"] = cape

    async def fetch_minecraftcapes_cape(self):
        """Fetch this players MinecraftCapes cape and stores it to :py:attr:`Player.minecraftcapes_cape`

        This is basically just an alias for :py:func:`utils.fetch_minecraftcapes_cape`"""
        cape = await fetch_minecraftcapes_cape(self)
        if cape:
            self._raw_capes["minecraftcapes"] = cape

    async def fetch_5zig_cape(self):
        """Fetch this players 5Zig cape and stores it to :py:attr:`Player.zig_cape`

        This is basically just an alias for :py:func:`utils.fetch_5zig_cape`"""
        cape = await fetch_5zig_cape(self)
        if cape:
            self._raw_capes["5zig"] = cape


class Skin:
    """Class representing a players skin

    Tip
    ----
    It's best practice to save the players skin to a database using :py:func:`encodeb64` and then
    reinitialize this class using :py:func:`decodeb64`. This way no API call is needed.\n
    Alternatively you can manually instantiate by passing a raw skin image.
    """

    def __init__(
            self,
            raw_skin,
            raw_skin_url=None,
            raw_cape=None,
            raw_cape_url=None,
    ):
        self._raw_skin: Image.Image = raw_skin
        self._raw_skin_url: Optional[str] = raw_skin_url
        self._raw_cape: Optional[Image.Image] = raw_cape
        self._raw_cape_url: Optional[str] = raw_cape_url

        self._skin: Optional[Image.Image] = None
        self._head: Optional[Image.Image] = None

        if self._raw_cape.mode != "RGBA":  # Converting capes to RGBA
            self._raw_cape = self._raw_cape.convert(mode="RGBA")

        if self._raw_skin.mode != "RGBA":  # Converting skins to RGBA
            self._raw_skin = self._raw_skin.convert(mode="RGBA")

        if self._raw_skin.height == 32:  # old skin format
            new_skin_im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            new_skin_im.paste(self._raw_skin, (0, 0))

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

    def __repr__(self):
        return f"<Skin (slim={self.is_slim}) (has_cape={self.has_cape})>"

    @property
    def skin(self):
        """The last skin which has been rendered using :py:func:`render_skin`"""
        return self._skin

    @property
    def head(self):
        """The last head which has been rendered using :py:func:`render_head`"""
        return self._head

    @property
    def raw_skin(self):
        """The players raw skin image"""
        return self._raw_skin

    @property
    def raw_skin_url(self):
        """The players skins url. Returns None if the skin has been manually passed"""
        return self._raw_skin_url

    @property
    def raw_cape(self):
        """The players raw cape image"""
        return self._raw_cape

    @property
    def raw_cape_url(self):
        """The players capes url. Returns None if the player doesn't have a cape or the cape has been manually passed"""
        return self._raw_cape_url

    @property
    def has_cape(self):
        """Whether the player has a cape or not"""
        return bool(self._raw_cape)

    @property
    def is_slim(self):
        """Whether the skin is slim (Alex type) or classic (Steve type)

        Only difference being the width of the arms (3px - 4px)"""
        return not bool(self._raw_skin.getpixel((46, 52))[3])

    def set_cape(self, cape: Image.Image):
        """Change the players cape

        Parameters
        ----------
        cape: Image
            The new cape image (64x32px)

        Raises
        ------
        ValueError
            Cape image has the wrong format or size
        """
        if cape.width != 64 or cape.height != 32:
            raise ValueError("Cape image must be 64x32 pixels")

        self._raw_cape = cape

    def show(self):
        """Shows the last rendered skin

        Alias for :py:func:`minepi.Skin.skin.show()`

        Raises
        ------
        ValueError
            No skin present
        """
        if self._skin:
            self._skin.show()
        else:
            raise ValueError()

    def encodeb64(self):
        """Base64 encodes the players skin and cape

        This allows for better caching and persistent storage in a database
        A :class:`Skin` class can then be recreated using :py:func:`decodeb64`

        Returns
        -------
        str
            The players skin and cape in format {raw_skin}-{raw_cape}"""
        with BytesIO() as buffered:
            self._raw_skin.save(buffered, format="PNG")
            buffered.seek(0)
            im_skin = buffered.getvalue()
        if self._raw_cape:
            with BytesIO() as buffered:
                self._raw_cape.save(buffered, format="PNG")
                buffered.seek(0)
                im_cape = buffered.getvalue()
        else:
            im_cape = None

        bytelist = [base64.b64encode(im_skin), base64.b64encode(im_cape)] if im_cape else [base64.b64encode(im_skin)]
        return b';'.join(bytelist).decode()

    @classmethod
    def decodeb64(cls, b64: str):
        """Create an instance of this class from a saved b64 string

        Parameters
        ----------
        b64: str
            The base64 encoded raw_skin image or raw_skin and raw_cape separated with a ";".
            Can be obtained from :py:func:`encodeb64`

        Returns
        -------
        :class:`Skin`
        """
        skin, cape = b64.split(";")
        skin.encode()
        if cape:
            cape.encode()

        im_str = base64.b64decode(skin)
        buffered = BytesIO(im_str)
        im_skin = Image.open(buffered)

        if cape:
            im_str = base64.b64decode(cape)
            buffered = BytesIO(im_str)
            im_cape = Image.open(buffered)
        else:
            im_cape = None

        return cls(raw_skin=im_skin, raw_cape=im_cape)

    async def render_skin(
            self,
            vr: int = 25,
            hr: int = 35,
            hrh: int = 0,
            vrll: int = 0,
            vrrl: int = 0,
            vrla: int = 0,
            vrra: int = 0,
            vrc: int = 30,
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
        vrc: int
            Vertical rotation of the cape
            Not actually in degrees, use random values please until you find one you like
        ratio: int
            Resolution of the returned image
        display_hair: bool
            Whether the second head layer is displayed
        display_second_layer: bool
            Whether the second skin layer is displayed
        display_cape: bool
            Whether the player's cape is shown
        aa: bool
            Antialiasing: smoothens the corners a bit

        Returns
        -------
        PIL.Image.Image
            The rendered skin
        """
        render = Render(
            player=self,
            vr=vr,
            hr=hr,
            hrh=hrh,
            vrll=vrll,
            vrrl=vrrl,
            vrla=vrla,
            vrra=vrra,
            vrc=vrc,
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
            Antialiasing: smoothens the corners a bit

        Returns
        -------
        PIL.Image.Image
            The rendered head
        """
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
