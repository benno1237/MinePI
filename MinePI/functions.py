from .skin_render import Render

import aiohttp
import json
from PIL import Image
import asyncio

class MinePI:
    async def render_3d_skin(
        user: str = "",
        vr: int = -25, 
        hr: int = 35, 
        hrh: int = 0, 
        vrll: int = 0, 
        vrrl: int = 0, 
        vrla: int = 0, 
        vrra: int = 0, 
        ratio: int = 12,
        display_hair: bool = True,
        display_second_layer: bool = True,
        aa: bool = False,
        skin_image: Image = None
        ):
        im = await Render(user, vr, hr, hrh, vrll, vrrl, vrla, vrra, ratio, False, display_hair, display_second_layer, aa).get_render(skin_image)
        return im

    async def render_3d_head(
        user: str = "",
        vr: int = -25, 
        hr: int = 35,  
        ratio: int = 12,
        display_hair: bool = True, 
        aa: bool = False,
        skin_image: Image = None
        ):
        im = await Render(user, vr, hr, 0, 0, 0, 0, 0, ratio, True, display_hair, False, aa).get_render(skin_image)
        return im

    async def get_skin(user: str):
        im = await Render(user, 0, 0, 0, 0, 0, 0, 0, 100, False, False, False, False).get_skin_mojang()
        return im

    async def to_uuid(
        name: str
    ):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.mojang.com/users/profiles/minecraft/{}".format(name)) as resp:
                uuid_dict = json.loads(await resp.text())
                try:
                    uuid = uuid_dict["id"]
                    return uuid
                except KeyError:
                    raise ValueError("Name {} is invalid".format(name))

    async def to_name(
        uuid: str,
        time: int = None
    ):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.mojang.com/user/profiles/{}/names".format(uuid)) as resp:
                name_dict = json.loads(await resp.text())
                if resp.status == 200:
                    if time == None:
                        max_entry = len(name_dict) - 1
                        name = name_dict[max_entry]["name"]
                        return name
                    else:
                        for i in range(len(name_dict) - 1, 0, -1):
                            if time > name_dict[i]["changedToAt"]:
                                return name_dict[i]["name"]
                        else:
                            return name_dict[0]["name"]
                elif resp.status == 400:
                    raise ValueError(name_dict["errorMessage"])
