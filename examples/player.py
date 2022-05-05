import asyncio
from minepi.player import Player

async def main():
    p = Player(uuid="1cb4b37f623d439d9528d17e3a452f0a")
    await p.initialize()
    print(p.name)
    print(p.is_slim)

    await p.render_skin()
    await p.render_head()
    p.skin.show()
    p.head.show()

asyncio.run(main())