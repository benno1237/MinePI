import asyncio
import base64
import json
from io import BytesIO
from typing import Optional

import aiohttp
from PIL import Image

from .skin import Skin
from .utils import (
    fetch_optifine_cape,
    fetch_labymod_cape,
    fetch_5zig_cape,
    fetch_minecraftcapes_cape,
    fetch_tlauncher_cape,
    name_to_uuid,
    uuid_to_undashed,
)
from .errors import InvalidPlayer


class Player:
    """Class representing a minecraft player
    This has to be created before a skin can be rendered

    Parameters
    ----------
    uuid: str
        UUID of the player (Not needed if name is given
    name: str
        Username of the player (Not needed if UUID is given)
    raw_skin: PIL.Image.Image
        Raw skin image of the player (64x64px)
    raw_cape: PIL.Image.Image
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
        if uuid is None and name is None:
            raise ValueError("Pass a username or UUID")

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
            "tlauncher": None,
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
    def labymod_cape(self):
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

    @property
    def tlauncher_cape(self):
        """The player's TLauncher cape"""
        return self._raw_capes["tlauncher"]

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

        Raises
        ------
        errors.InvalidPlayer
            Player does not seem to be valid
        """
        if not self._session:
            self._session = aiohttp.ClientSession()
            self._close_session = True

        if self._uuid is None:
            uuid = await name_to_uuid(self._username, self._session)
            if uuid:
                self._uuid = uuid_to_undashed(uuid)

        textures = None
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
                        raise InvalidPlayer()

        if textures is not None:
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
        """Fetches the players optifine cape and stores it to :py:attr:`Player.optifine_cape`
        
        This is basically just an alias for :py:func:`utils.fetch_optifine_cape`"""
        cape = await fetch_optifine_cape(self)
        if cape is not None:
            self._raw_capes["optifine"] = cape

    async def fetch_labymod_cape(self):
        """Fetches the players labymod cape and stores it to :py:attr:`Player.labymod_cape`

        This is basically just an alias for :py:func:`utils.fetch_labymod_cape`"""
        cape = await fetch_labymod_cape(self)
        if cape is not None:
            self._raw_capes["labymod"] = cape

    async def fetch_minecraftcapes_cape(self):
        """Fetches the players MinecraftCapes cape and stores it to :py:attr:`Player.minecraftcapes_cape`

        This is basically just an alias for :py:func:`utils.fetch_minecraftcapes_cape`"""
        cape = await fetch_minecraftcapes_cape(self)
        if cape is not None:
            self._raw_capes["minecraftcapes"] = cape

    async def fetch_5zig_cape(self):
        """Fetches the players 5Zig cape and stores it to :py:attr:`Player.zig_cape`

        This is basically just an alias for :py:func:`utils.fetch_5zig_cape`"""
        cape = await fetch_5zig_cape(self)
        if cape is not None:
            self._raw_capes["5zig"] = cape

    async def fetch_tlauncher_cape(self):
        """Fetches the players TLauncher cape and stores it to :py:attr:`Player.tlauncher_cape`

        This is basically just an alias for :py:func:`utils.fetch_tlauncher_cape`"""
        cape = await fetch_tlauncher_cape()
        if cape is not None:
            self._raw_capes["tlauncher"] = cape
