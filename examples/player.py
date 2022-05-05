import asyncio
from minepi import Player

async def main():
    p = Player(uuid="1cb4b37f623d439d9528d17e3a452f0a")  # create a Player object by UUID
    await p.initialize()  # initialize the Player object

    await p.render_skin()
    await p.render_head()
    p.skin.show()
    p.head.show()

asyncio.run(main())