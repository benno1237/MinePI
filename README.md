# MinePI
## _The Minecraft Utility Library Of Your Choice!_

![Build Status](https://travis-ci.org/joemccann/dillinger.svg?branch=master)

MinePI is a Minecraft Utility Library that uses the MojangAPI

## Features

- Render full Minecraft Skins
- Render Minecraft Heads
- convert usernames to UUIDs
- convert UUIDs to usernames

## Usage

### `await get_3d_skin`
This function is a [coroutine](https://docs.python.org/3/library/asyncio-task.html)

#### Parameters
- `user` (Optional[str]) - Username or UUID of the player
- `vr` (Optional[int], default = -25) - vertical rotation
- `hr` (Optional[int], default = 35) - horizontal rotation
- `hrh` (Optional[int], default = 0) - horizontal head rotation
- `vrll` (Optional[int], default = 0) - vertical left leg angle
- `vrrl` (Optional[int], default = 0) - vertical right leg angle
- `vrla` (Optional[int], default = 0) - vertical left arm angle
- `vrra` (Optional[int], default = 0) - vertical right arm angle
- `ratio` (Optional[int], default = 12) - size of the returned image
- `display_hair` (Optional[bool], default = True) - display players "helmet"
- `display_second_layer` (Optional[bool], default = True) - display second skin layer
- `aa` (Optional[bool], default = False) - antializing: improves corner quality by rendering with `ratio * 2` and scaling it down to `ratio`
- `skin_image` (Optional[[PIL.Image.Image](https://pillow.readthedocs.io/en/stable/reference/Image.html)], default = None) - minecraft skin image to prevent the script from looking it up

#### Returns
- [`Image`](https://pillow.readthedocs.io/en/stable/reference/Image.html) - the rendered skin 

### `await get_3d_head`
This function is a [coroutine](https://docs.python.org/3/library/asyncio-task.html)

#### Parameters
- `user` (Optional[str]) - Username or UUID of the player
- `vr` (Optional[int], default = -25) - vertical rotation
- `hr` (Optional[int], default = 35) - horizontal rotation
- `ratio` (Optional[int], default = 12) - size of the returned image
- `display_hair` (Optional[bool], default = True) - display players "helmet"
- `aa` (Optional[bool], default = False) - antializing: improves corner quality by rendering with `ratio * 2` and scaling it down to `ratio`
- `skin_image` (Optional[[PIL.Image.Image](https://pillow.readthedocs.io/en/stable/reference/Image.html)], default = None) - minecraft skin image to prevent the script from looking it up

#### Returns
- [`Image`](https://pillow.readthedocs.io/en/stable/reference/Image.html) - the rendered head 

### `await get_skin`
This function is a [coroutine](https://docs.python.org/3/library/asyncio-task.html)

#### Parameters
- `user` (Required[str]) - Username or UUID of the player

#### Returns
- [`Image`](https://pillow.readthedocs.io/en/stable/reference/Image.html) - the skin image returned by the MojangAPI

### `await to_uuid`
This function is a [coroutine](https://docs.python.org/3/library/asyncio-task.html)

#### Parameters
- `name` (Required[str]) - Username that should be converted into a UUID

#### Returns
- `uuid` [str] - Players UUID

### `await to_name`
This function is a [coroutine](https://docs.python.org/3/library/asyncio-task.html)

#### Parameters
- `uuid` (Required[str]) - UUID that should be converted into a username
- `time` (Optional[int]) - Must be in UNIX time

#### Returns
- `name` [str] - Players username at the given time (current if not given)

## Installation

```sh
pip install MinePI
```
