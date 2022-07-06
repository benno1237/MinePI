import typing
import aiohttp

from PIL import Image
from io import BytesIO
from typing import Optional

if typing.TYPE_CHECKING:
    from .player import Player


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
            name = await resp.json()["name"]
        else:
            name = None

    if close:
        await session.close()

    return name


async def fetch_optifine_cape(
        player: "Player" = None,
        name: str = None,
        uuid: str = None,
        session: aiohttp.ClientSession = None
):
    """Fetch a players optifine cape

    Note
    ----
    Passing a :class:`Player` object is recommended. If none is available or you want to fetch
    a different players optifine cape, a name or UUID can be passed. Names are prefered over UUID's
    in this case since they require one API call less.

    Parameters
    ----------
    player: Player
        The player to fetch the optifine cape for
    name: str
        Minecraft username to fetch the optifine cape for
    uuid: str
        UUID of the player to fetch the optifine cape for
    session: aiohttp.ClientSession
        The ClientSession to use for requests
        Defaults to a new session which is closed again after handling all requests

    Returns
    -------
    Optional[Image]
        None if the given player has no optifine cape

    Raises
    ------
    ValueError
        No player or name or uuid has been passed
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

    if name is not None:
        async with session.get(f"http://s.optifine.net/capes/{name}") as resp:
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
):
    """Fetch a players labymod cape

    Note
    ----
    Passing a :class:`Player` object is recommended. If none is available or you want to fetch
    a different players labymod cape, a name or UUID can be passed. UUIDs are prefered over names
    in this case since they require one API call less.

    Parameters
    ----------
    player: Player
        The player to fetch the labymod cape for
    name: str
        Minecraft username to fetch the labymod cape for
    uuid: str
        UUID of the player to fetch the labymod cape for
    session: aiohttp.ClientSession
        The ClientSession to use for requests
        Defaults to a new session which is closed again after handling all requests

    Returns
    -------
    Optional[Image]
        None if the given player has no labymod cape

    Raises
    ------
    ValueError
        No player or name or uuid has been passed
    """
    if player is None and name is None and uuid is None:
        raise ValueError

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
        async with session.get(f"https://api.labymod.net/capes/capecreator/capedata.php?username={name}") as resp:
            if resp.status == 200:
                cape_url = (await resp.json())["cape_url"]
            else:
                cape_url = None

        if cape_url:
            async with session.get(cape_url) as resp:
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
):
    """Fetch a players 5Zig cape

    Note
    ----
    Passing a :class:`Player` object is recommended. If none is available or you want to fetch
    a different players 5Zig cape, a name or UUID can be passed. UUIDs are prefered over names
    in this case since they require one API call less.

    Parameters
    ----------
    player: Player
        The player to fetch the 5Zig cape for
    name: str
        Minecraft username to fetch the 5Zig cape for
    uuid: str
        UUID of the player to fetch the 5Zig cape for
    session: aiohttp.ClientSession
        The ClientSession to use for requests
        Defaults to a new session which is closed again after handling all requests

    Returns
    -------
    Optional[Image]
        None if the given player has no 5Zig cape

    Raises
    ------
    ValueError
        No player or name or uuid has been passed
    """
    if player is None and name is None and uuid is None:
        raise ValueError

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
        if len(uuid) == 28:
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
):
    """Fetch a players MinecraftCapes cape

    Note
    ----
    Passing a :class:`Player` object is recommended. If none is available or you want to fetch
    a different players MinecraftCapes cape, a name or UUID can be passed. Names are prefered over UUID's
    in this case since they require one API call less.

    Parameters
    ----------
    player: Player
        The player to fetch the MinecraftCapes cape for
    name: str
        Minecraft username to fetch the MinecraftCapes cape for
    uuid: str
        UUID of the player to fetch the MinecraftCapes cape for
    session: aiohttp.ClientSession
        The ClientSession to use for requests
        Defaults to a new session which is closed again after handling all requests

    Returns
    -------
    Optional[Image]
        None if the given player has no MinecraftCapes cape

    Raises
    ------
    ValueError
        No player or name or uuid has been passed
    """
    if player is None and name is None and uuid is None:
        raise ValueError()

    if not session:
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
        async with session.get(f"https://www.minecraftcapes.co.uk/getCape.php?u={name}") as resp:
            if resp.status == 200:
                cape = Image.open(BytesIO(await resp.read()))
            else:
                cape = None
    else:
        cape = None

    if close:
        await session.close()

    return cape


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
