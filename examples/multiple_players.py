import asyncio
import aiohttp
import minepi

async def main():
    session = aiohttp.ClientSession()  # creating our own ClientSession since we can reuse it
    usernames = [
        "sucr_kolli",
        "Herobrine",
        "Technoblade"
    ]

    players = await minepi.get_players_by_name(usernames, session=session)
    await asyncio.gather(*[p.initialize() for p in players])  # initializes all Player objects

    print(players)

    await session.close()

asyncio.run(main())