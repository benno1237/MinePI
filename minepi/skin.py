import base64

from typing import Optional
from PIL import Image, ImageOps
from io import BytesIO

from .skin_render import Render
from .errors import NoRenderedSkin

class Skin:
    """
    Tip
    ----
    It's best practice to save the players skin to a database using :py:func:`encodeb64` and then
    reinitialize this class using :py:func:`decodeb64`. This way no API call is needed.\n
    Alternatively you can manually instantiate by passing a raw skin image.

    Parameters
    ----------
    raw_skin: PIL.Image.Image
        The raw skin image
    raw_cape: PIL.Image.Image
        The raw cape image
    """

    def __init__(
            self,
            raw_skin,
            raw_cape=None,
            raw_skin_url=None,
            raw_cape_url=None,
            name=None,
    ):
        self._raw_skin: Image.Image = raw_skin
        self._raw_skin_url: Optional[str] = raw_skin_url
        self._raw_cape: Optional[Image.Image] = None
        self._raw_cape_url: Optional[str] = raw_cape_url
        self._name: Optional[str] = name

        self._skin: Optional[Image.Image] = None
        self._head: Optional[Image.Image] = None

        if raw_cape is not None:
            self.set_cape(raw_cape)

        if self._raw_skin.mode != "RGBA":  # Converting skins to RGBA
            self._raw_skin = self._raw_skin.convert(mode="RGBA")

        if self._raw_skin.height == 32:  # old skin format
            new_skin_im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            new_skin_im.paste(self._raw_skin, (0, 0))

            for i in range(2):
                f1 = 40 if i != 0 else 0
                f2 = 16 if i != 0 else 0

                new_skin_im.paste(ImageOps.mirror(self._raw_skin.crop((4+f1, 16, 8+f1, 20))), (20+f2, 48))
                new_skin_im.paste(ImageOps.mirror(self._raw_skin.crop((8+f1, 16, 12+f1, 20))), (24+f2, 48))
                new_skin_im.paste(ImageOps.mirror(self._raw_skin.crop((8+f1, 20, 12+f1, 32))), (16+f2, 52))
                new_skin_im.paste(ImageOps.mirror(self._raw_skin.crop((12+f1, 20, 16+f1, 32))), (20+f2, 52))
                new_skin_im.paste(ImageOps.mirror(self._raw_skin.crop((4+f1, 20, 8+f1, 32))), (24+f2, 52))
                new_skin_im.paste(ImageOps.mirror(self._raw_skin.crop((0+f1, 20, 4+f1, 32))), (28+f2, 52))

            self._raw_skin = new_skin_im

    def __repr__(self):
        return f"<Skin (slim={self.is_slim}) (has_cape={self.has_cape})>"

    @property
    def skin(self):
        """The last skin which has been rendered using :py:func:`render_skin`"""
        return self._skin

    @property
    def head(self):
        """The last head which has been rendered using :py:func:`render_head`"""
        return self._head

    @property
    def raw_skin(self):
        """The players raw skin image"""
        return self._raw_skin

    @property
    def raw_skin_url(self):
        """The players skins url. Returns None if the skin has been manually passed"""
        return self._raw_skin_url

    @property
    def raw_cape(self):
        """The players raw cape image"""
        return self._raw_cape

    @property
    def raw_cape_url(self):
        """The players capes url. Returns None if the player doesn't have a cape or the cape has been manually passed"""
        return self._raw_cape_url

    @property
    def has_cape(self):
        """Whether the player has a cape"""
        return bool(self._raw_cape)

    @property
    def is_slim(self):
        """Whether the skin is slim (Alex type) or classic (Steve type)

        Only difference being the width of the arms (3px - 4px)"""
        return not bool(self._raw_skin.getpixel((46, 52))[3])

    def set_cape(self, cape: Image.Image):
        """Change the players cape

        Parameters
        ----------
        cape: PIL.Image.Image
            The new cape image (64x32px)
        """
        # attempt to detect wrongly scaled mojang capes
        if cape.width / cape.height == 2 and (cape.width != 64 or cape.height != 32):
            cape.resize((64, 32), resample=Image.LANCZOS)

        if cape.width == 22 and cape.height == 17:  # Labymod
            pass

        if cape.width == 64 and cape.height > 32:  # MinecraftCapes animated
            pass

        if cape.mode != "RGBA":  # Converting capes to RGBA
            cape = cape.convert(mode="RGBA")

        self._raw_cape = cape

    def show(self):
        """Shows the last rendered skin

        Alias for :py:func:`Skin.skin.show()`

        Raises
        ------
        NoRenderedSkin
            No skin present. Generate a render using :py:func:`render_skin`
        """
        if self._skin:
            self._skin.show()
        else:
            raise NoRenderedSkin()

    def encodeb64(self):
        """Base64 encodes the players skin and cape

        This allows for better caching and persistent storage in a database
        A :class:`Skin` class can then be recreated using :py:func:`decodeb64`

        Returns
        -------
        str
            The players skin and cape in format {raw_skin}-{raw_cape}"""
        with BytesIO() as buffered:
            self._raw_skin.save(buffered, format="PNG")
            buffered.seek(0)
            im_skin = buffered.getvalue()
        if self._raw_cape:
            with BytesIO() as buffered:
                self._raw_cape.save(buffered, format="PNG")
                buffered.seek(0)
                im_cape = buffered.getvalue()
        else:
            im_cape = None

        bytelist = [base64.b64encode(im_skin), base64.b64encode(im_cape)] if im_cape else [base64.b64encode(im_skin)]
        return b';'.join(bytelist).decode()

    @classmethod
    def decodeb64(cls, b64: str):
        """Create an instance of this class from a saved b64 string

        Parameters
        ----------
        b64: str
            The base64 encoded raw_skin image or raw_skin and raw_cape separated with a ";".
            Can be obtained from :py:func:`encodeb64`

        Returns
        -------
        :class:`Skin`
        """
        skin, cape = b64.split(";")
        skin.encode()
        if cape:
            cape.encode()

        im_str = base64.b64decode(skin)
        buffered = BytesIO(im_str)
        im_skin = Image.open(buffered)

        if cape:
            im_str = base64.b64decode(cape)
            buffered = BytesIO(im_str)
            im_cape = Image.open(buffered)
        else:
            im_cape = None

        return cls(raw_skin=im_skin, raw_cape=im_cape)

    async def render_skin(
            self,
            vr: int = 25,
            hr: int = 35,
            hrh: int = 0,
            vrll: int = 0,
            vrrl: int = 0,
            vrla: int = 0,
            vrra: int = 0,
            vrc: int = 30,
            ratio: int = 12,
            display_hair: bool = True,
            display_second_layer: bool = True,
            display_cape: bool = True,
            aa: bool = False,
    ) -> Optional[Image.Image]:
        """Render a full body skin

        Parameters
        ----------
        vr: int
            Vertical rotation of the output image
        hr: int
            Horizontal rotation of the output image
        hrh: int
            Horizontal head rotation
        vrll: int
            Vertical rotation of the left leg
        vrrl: int
            Vertical rotation of the right leg
        vrla: int
            Vertical rotation of the left arm
        vrra: int
            Vertical rotation of the right arm
        vrc: int
            Vertical rotation of the cape
            Not actually in degrees, use random values please until you find one you like
        ratio: int
            Resolution of the returned image
        display_hair: bool
            Whether the second head layer is displayed
        display_second_layer: bool
            Whether the second skin layer is displayed
        display_cape: bool
            Whether the player's cape is shown
        aa: bool
            Antialiasing: smoothens the corners a bit

        Returns
        -------
        PIL.Image.Image
            The rendered skin
        """
        render = Render(
            player=self,
            vr=vr,
            hr=hr,
            hrh=hrh,
            vrll=vrll,
            vrrl=vrrl,
            vrla=vrla,
            vrra=vrra,
            vrc=vrc,
            ratio=ratio,
            head_only=False,
            display_hair=display_hair,
            display_layers=display_second_layer,
            display_cape=display_cape,
            aa=aa,
        )
        im = await render.get_render()
        self._skin = im
        return im

    async def render_head(
            self,
            vr: int = 25,
            hr: int = 35,
            ratio: int = 12,
            display_hair: bool = True,
            aa: bool = False,
    ) -> Optional[Image.Image]:
        """Render the players head

        Parameters
        ----------
        vr: int
            Vertical rotation of the output image
        hr: int
            Horizontal rotation of the output image
        ratio: int
            Resolution of the returned image
        display_hair: bool
            Whether or not the second head layer should be displayed
        aa: bool
            Antialiasing: smoothens the corners a bit

        Returns
        -------
        PIL.Image.Image
            The rendered head
        """
        render = Render(
            player=self,
            vr=vr,
            hr=hr,
            ratio=ratio,
            head_only=True,
            display_hair=display_hair,
            aa=aa,
        )
        im = await render.get_render()
        self._head = im
        return im
