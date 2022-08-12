import base64
import typing
import aiohttp
import json

from PIL import Image
from io import BytesIO
from typing import Optional

from .skin import Skin

if typing.TYPE_CHECKING:
    from .player import Player


__all__ = [
    "uuid_to_dashed",
    "uuid_to_undashed",
    "name_to_uuid",
    "uuid_to_name",
    "fetch_skin",
    "fetch_optifine_cape",
    "fetch_labymod_cape",
    "fetch_5zig_cape",
    "fetch_minecraftcapes_cape",
    "fetch_tlauncher_cape",
    "get_players_by_name",
]


def uuid_to_dashed(uuid: str) -> str:
    """Converts a not dashed UUID to a dashed one

    Parameters
    ----------
    uuid: str
        The UUID to convert

    Returns
    -------
    str
        The converted UUID
    """
    return f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"


def uuid_to_undashed(uuid: str) -> str:
    """Converts a dashed UUID to a not dashed one

    Parameters
    ----------
    uuid: str
        The UUID to convert

    Returns
    -------
    str
        The converted UUID
    """
    return uuid.replace("-", "")


async def name_to_uuid(name: str, session: aiohttp.ClientSession = None) -> Optional[str]:
    """Convert a minecraft name to a UUID

    Parameters
    ----------
    name: str
        The minecraft name to get the UUID for
    session: aiohttp.ClientSession
        The ClientSession to use for requests
        Defaults to a new session which is closed again after handling all requests

    Returns
    -------
    Optional[str]
        None if the given name is invalid
    """
    if session is None:
        session = aiohttp.ClientSession()
        close = True
    else:
        close = False

    async with session.get(f"https://api.mojang.com/users/profiles/minecraft/{name}") as resp:
        if resp.status == 200:
            uuid = (await resp.json())["id"]
        else:
            uuid = None

    if close:
        await session.close()

    return uuid


async def uuid_to_name(uuid: str, session: aiohttp.ClientSession = None) -> Optional[str]:
    """Convert a UUID to a minecraft name

    Parameters
    ----------
    uuid: str
        The UUID to get the minecraft name for
    session: aiohttp.ClientSession
        The ClientSession to use for requests
        Defaults to a new session which is closed again after handling all requests

    Returns
    -------
    Optional[str]
        None if the given UUID is invalid
    """
    if session is None:
        session = aiohttp.ClientSession()
        close = True
    else:
        close = False

    async with session.get(
            f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}"
    ) as resp:
        if resp.status == 200:
            name = (await resp.json())["name"]
        else:
            name = None

    if close:
        await session.close()

    return name


async def fetch_skin(
        player: "Player" = None,
        name: str = None,
        uuid: str = None,
        session: aiohttp.ClientSession = None
) -> Optional[Skin]:
    """Fetch a players skin

    Note
    ----
    This function also returns the players mojang cape (if available).

    Tip
    ----
    Passing a :py:class:`minepi.Player` is recommended. If none is available, a name or UUID can be passed.
    UUIDs are preferred over names in this case since they require one API call less.

    Parameters
    ----------
    player: Player
        The player to fetch the skin for
    name: str
        Minecraft username to fetch the skin for
    uuid: str
        UUID to fetch the skin for
    session: aiohttp.ClientSession
        The ClientSession to use for requests
        Defaults to a new session which is closed again after handling all requests

    Returns
    -------
    Skin
        A fully functional :py:class:`minepi.Skin` class

    Raises
    ------
    ValueError
        No :py:class:`minepi.Player`, name or UUID has been passed
    """
    if player is None and name is None and uuid is None:
        raise ValueError("At least one parameter must be passed")

    if session is None:
        session = aiohttp.ClientSession()
        close = True
    else:
        close = False

    if player and player.uuid is not None:
        uuid = player.uuid

    if uuid is None and name is not None:
        uuid = await name_to_uuid(name, session)

    if uuid is not None:
        async with session.get(
            f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}"
        ) as resp:
            if resp.status == 200:
                cape = None
                skin = None
                resp_dict = await resp.json()
                for p in resp_dict["properties"]:
                    if p["name"] == "textures":
                        textures = json.loads(base64.b64decode(p["value"]))["textures"]
                        skin_url = textures["SKIN"]["url"]
                        cape_url = textures["CAPE"]["url"] if "CAPE" in textures.keys() else None

                        if skin_url:
                            async with session.get(skin_url) as resp_skin:
                                if resp.status == 200:
                                    skin = Image.open(BytesIO(await resp_skin.read()))

                        if cape_url:
                            async with session.get(cape_url) as resp_cape:
                                if resp.status == 200:
                                    cape = Image.open(BytesIO(await resp_cape.read()))
                        break

    if close is True:
        await session.close()

    if skin is None:
        raise ValueError

    return Skin(
        raw_skin=skin,
        raw_cape=cape,
        raw_skin_url=skin_url,
        raw_cape_url=cape_url,
        name=resp_dict["name"]
    )


async def fetch_mojang_cape(
        player: "Player" = None,
        name: str = None,
        uuid: str = None,
        session: aiohttp.ClientSession = None
) -> Optional[Image.Image]:
    """Fetch a players mojang cape

    Tip
    ----
    Passing a :py:class:`minepi.Player` object is recommended. If none is available, a name or UUID can be passed.
    UUIDs are preferred over names in this case since they require one API call less.

    Parameters
    ----------
    player: Player
        The player to fetch the mojang cape for
    name: str
        Minecraft username to fetch the mojang cape for
    uuid: str
        UUID to fetch the mojang cape for
    session: aiohttp.ClientSession
        The ClientSession to use for requests
        Defaults to a new session which is closed again after handling all requests

    Returns
    -------
    Optional[PIL.Image.Image]
        None if the given player has no mojang cape

    Raises
    ------
    ValueError
        No :py:class:`minepi.Player`, name or UUID has been passed
    """
    s = await fetch_skin(player=player, name=name, uuid=uuid, session=session)
    return s.raw_cape if s is not None else None


async def fetch_optifine_cape(
        player: "Player" = None,
        name: str = None,
        uuid: str = None,
        session: aiohttp.ClientSession = None
) -> Optional[Image.Image]:
    """Fetch a players optifine cape

    Tip
    ----
    Passing a :py:class:`minepi.Player` object is recommended. If none is available, a name or UUID can be passed.
    Names are preferred over UUIDs in this case since they require one API call less.

    Parameters
    ----------
    player: Player
        The player to fetch the optifine cape for
    name: str
        Minecraft username to fetch the optifine cape for
    uuid: str
        UUID to fetch the optifine cape for
    session: aiohttp.ClientSession
        The ClientSession to use for requests
        Defaults to a new session which is closed again after handling all requests

    Returns
    -------
    Optional[PIL.Image.Image]
        None if the given player has no optifine cape

    Raises
    ------
    ValueError
        No :py:class:`minepi.Player`, name or UUID has been passed
    """
    if player is None and name is None and uuid is None:
        raise ValueError("At least one parameter must be passed")

    if session is None:
        session = aiohttp.ClientSession()
        close = True
    else:
        close = False

    if player is not None:
        name = player.name
    elif name is not None:
        pass
    else:
        name = await uuid_to_name(uuid, session)

    if name is not None:
        async with session.get(f"http://s.optifine.net/capes/{name}.png") as resp:
            if resp.status == 200:
                cape = Image.open(BytesIO(await resp.read()))
            else:
                cape = None
    else:
        cape = None

    if close:
        await session.close()

    return cape


async def fetch_labymod_cape(
        player: "Player" = None,
        name: str = None,
        uuid: str = None,
        session: aiohttp.ClientSession = None
) -> Optional[Image.Image]:
    """Fetch a players labymod cape

    Tip
    ----
    Passing a :py:class:`minepi.Player` object is recommended. If none is available, a name or UUID can be passed.
    UUIDs are preferred over names in this case since they require one API call less.

    Parameters
    ----------
    player: Player
        The player to fetch the labymod cape for
    name: str
        Minecraft username to fetch the labymod cape for
    uuid: str
        UUID to fetch the labymod cape for
    session: aiohttp.ClientSession
        The ClientSession to use for requests
        Defaults to a new session which is closed again after handling all requests

    Returns
    -------
    Optional[PIL.Image.Image]
        None if the given player has no labymod cape

    Raises
    ------
    ValueError
        No :py:class:`minepi.Player`, name or UUID has been passed
    """
    if player is None and name is None and uuid is None:
        raise ValueError("At least one parameter must be passed")

    if session is None:
        session = aiohttp.ClientSession()
        close = True
    else:
        close = False

    if player is not None:
        uuid = player.uuid
    elif uuid is not None:
        pass
    else:
        uuid = await name_to_uuid(name, session)

    if uuid is not None:
        if len(uuid) == 32:
            uuid = uuid_to_dashed(uuid)

        async with session.get(f"https://dl.labymod.net/capes/{uuid}") as resp:
            if resp.status == 200:
                cape = Image.open(BytesIO(await resp.read()))
            else:
                cape = None
    else:
        cape = None

    if close:
        await session.close()

    return cape


async def fetch_5zig_cape(
        player: "Player" = None,
        name: str = None,
        uuid: str = None,
        session: aiohttp.ClientSession = None
) -> Optional[Image.Image]:
    """Fetch a players 5Zig cape

    Tip
    ----
    Passing a :class:`minepi.Player` object is recommended. If none is available, a name or UUID can be passed.
    UUIDs are preferred over names in this case since they require one API call less.

    Warning
    -------
    5zig capes are not guaranteed to work yet.
    If you own an account with 5zigreborn cape, it would be very helpful if you could send us the
    username.

    Parameters
    ----------
    player: Player
        The player to fetch the 5Zig cape for
    name: str
        Minecraft username to fetch the 5Zig cape for
    uuid: str
        UUID to fetch the 5Zig cape for
    session: aiohttp.ClientSession
        The ClientSession to use for requests
        Defaults to a new session which is closed again after handling all requests

    Returns
    -------
    Optional[PIL.Image.Image]
        None if the given player has no 5Zig cape

    Raises
    ------
    ValueError
        No :py:class:`minepi.Player`, name or UUID has been passed
    """
    if player is None and name is None and uuid is None:
        raise ValueError("At least one parameter must be passed")

    if session is None:
        session = aiohttp.ClientSession()
        close = True
    else:
        close = False

    if player is not None:
        uuid = player.uuid
    elif uuid is not None:
        pass
    else:
        uuid = await name_to_uuid(name, session)

    if uuid is not None:
        if len(uuid) == 32:
            uuid = uuid_to_dashed(uuid)

        async with session.get(f"https://textures.5zigreborn.eu/profile/{uuid}") as resp:
            if resp.status == 200:
                cape = Image.open(BytesIO(await resp.read()))
            else:
                cape = None
    else:
        cape = None

    if close:
        await session.close()

    return cape


async def fetch_minecraftcapes_cape(
        player: "Player" = None,
        name: str = None,
        uuid: str = None,
        session: aiohttp.ClientSession = None
) -> Optional[Image.Image]:
    """Fetch a players MinecraftCapes cape

    Tip
    ----
    Passing a :py:class:`minepi.Player` object is recommended. If none is available, a name or UUID can be passed.
    UUIDs are preferred over names in this case since they require one API call less.

    Warning
    -------
    Animated MinecraftCapes capes are not supported yet

    Parameters
    ----------
    player: Player
        The player to fetch the MinecraftCapes cape for
    name: str
        Minecraft username to fetch the MinecraftCapes cape for
    uuid: str
        UUID to fetch the MinecraftCapes cape for
    session: aiohttp.ClientSession
        The ClientSession to use for requests
        Defaults to a new session which is closed again after handling all requests

    Returns
    -------
    Optional[PIL.Image.Image]
        None if the given player has no MinecraftCapes cape

    Raises
    ------
    ValueError
        No :py:class:`minepi.Player`, name or UUID has been passed
    """
    if player is None and name is None and uuid is None:
        raise ValueError("At least one parameter must be passed")

    if not session:
        session = aiohttp.ClientSession()
        close = True
    else:
        close = False

    if player is not None:
        uuid = player.uuid
    elif uuid is not None:
        pass
    else:
        uuid = await name_to_uuid(name, session)

    if uuid is not None:
        if len(uuid) == 36:
            uuid = uuid_to_undashed(uuid)

        async with session.get(f"https://minecraftcapes.net/profile/{uuid}/cape") as resp:
            if resp.status == 200:
                cape = Image.open(BytesIO(await resp.read()))
            else:
                cape = None
    else:
        cape = None

    if close:
        await session.close()

    return cape


async def fetch_tlauncher_cape(
        player: "Player" = None,
        name: str = None,
        uuid: str = None,
        session: aiohttp.ClientSession = None
) -> Optional[Image.Image]:
    """Fetch a players TLauncher cape

    Tip
    ----
    Passing a :py:class:`minepi.Player` object is recommended. If none is available, a name or UUID can be passed.
    Names are preferred over UUIDs in this case since they require one API call less.


    Warning
    -------
    TLauncher capes are still experimental and not guaranteed to work.
    If you want to help implement them further, please get in touch with me.
    If you could share a few account names with TLauncher capes (especially animated ones),
    that would help us a lot.

    Parameters
    ----------
    player: Player
        The player to fetch the TLauncher cape for
    name: str
        Minecraft username to fetch the TLauncher cape for
    uuid: str
        UUID to fetch the TLauncher cape for
    session: aiohttp.ClientSession
        The ClientSession to use for requests
        Defaults to a new session which is closed again after handling all requests

    Returns
    -------
    Optional[PIL.Image.Image]
        None if the given player has no TLauncher cape

    Raises
    ------
    ValueError
        No :py:class:`minepi.Player`, name or UUID has been passed
    """
    if player is None and name is None and uuid is None:
        raise ValueError()

    if session is None:
        session = aiohttp.ClientSession()
        close = True
    else:
        close = False

    if player is not None:
        name = player.name
    elif name is not None:
        pass
    else:
        name = await uuid_to_name(uuid, session)

    cape = None
    if name is not None:
        async with session.get(f"https://auth.tlauncher.org/skin/profile/texture/login/{name}") as resp:
            if resp.status == 200:
                resp_dict = await resp.json()
                cape_url = resp_dict["CAPE"]["url"] if "CAPE" in resp_dict.keys() else None
            else:
                cape_url = None

        if cape_url is not None:
            if not cape_url.startswith("http://textures.minecraft.net/"):
                async with session.get(cape_url) as resp:
                    if resp.status == 200:
                        cape = Image.open(BytesIO(await resp.read()))

    if close:
        await session.close()

    return cape


async def get_players_by_name(names: list, session: aiohttp.ClientSession = None):
    """Useful helper function to get multiple :py:class:`minepi.Player` objects

    Only does one API call for the entire list instead of one per player
    This is recommended to be used if you have a list of usernames

    Parameters
    ----------
    names: list
        A list of minecraft usernames
    session: aiohttp.ClientSession
        The ClientSession to use for requests
        Defaults to a new session which is closed again after handling all requests

    Returns
    -------
    list
        A list of :py:class:`minepi.Player` objects
    """
    if session is None:
        session = aiohttp.ClientSession()
        close = True
    else:
        close = False

    players = []
    async with session.post("https://api.mojang.com/profiles/minecraft", json=names) as resp:
        if resp.status == 200:
            for entry in await resp.json():
                players.append(Player(uuid=entry["id"], name=entry["name"], session=session if not close else None))

    if close:
        await session.close()

    return players
