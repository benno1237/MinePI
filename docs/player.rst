******
Player
******

Class representing a Minecraft player.
This class is used to fetch and store player data from the Mojang API.

.. note:: This class needs an active network connection.

~~~~~~~~~~~
Basic Usage
~~~~~~~~~~~
.. code-block:: python

    from minepi import Player

    p = Player(name="sucr_kolli")  # get player by name
    await p.initialize()  # fetch all data

~~~~~~~~~~~~~
API Reference
~~~~~~~~~~~~~
.. autoclass:: minepi.Player
    :autosummary:
    :autosummary-nosignatures:
    :members:

****
Skin
****

Class representing a Minecraft skin

.. note:: Everything in this class works completely offline, even
          the render itself.

~~~~~~~~~~~
Basic Usage
~~~~~~~~~~~
.. code-block:: python

    from minepi import Skin
    from PIL import Image

    raw_skin = Image.open(path_to_skin)
    raw_cape = Image.open(path_to_cape)  # Optional
    s = Skin(raw_skin=raw_skin, raw_cape=raw_cape)

    await s.render_skin()
    s.skin.show()

~~~~~~~~~~~~~
API Reference
~~~~~~~~~~~~~
.. autoclass:: minepi.Skin
    :autosummary:
    :autosummary-nosignatures:
    :members:

*****
Utils
*****

~~~~~~~~~~~~~
API Reference
~~~~~~~~~~~~~
.. automodule:: minepi.utils
    :autosummary:
    :autosummary-nosignatures:
    :members: