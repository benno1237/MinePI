*************
Example Usage
*************

.. code-block:: python

    from minepi import Player
    import asyncio

    async def main():
        player = Player(name="sucr_kolli")
        await player.initialize()

        await player.render_skin()
        player.skin.show()

    asyncio.run(main())