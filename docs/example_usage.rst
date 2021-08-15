*************
Example Usage
*************

.. code-block:: python

    import MinePI
    import asyncio

    async def main():
        #Render a full body skin
        im = await MinePI.render_3d_skin("Herobrine")

        #Render a head only skin
        im = await MinePI.render_3d_head("Herobrine")

    asyncio.run(main())