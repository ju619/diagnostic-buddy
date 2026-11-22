"""Open the smear image in the same orientation the user sees when marking it."""
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError


FONT = Path(__file__).resolve().parent / "fonts" / "Vera.ttf"
MAX_PIXELS = 12_000_000


class InvalidImage(ValueError):
    pass


def decode(data):
    try:
        with Image.open(BytesIO(data), formats=("PNG", "JPEG")) as image:
            width, height = image.size
            if min(width, height) < 48 or width * height > MAX_PIXELS:
                raise InvalidImage("Use an image at least 48 pixels on each side and no larger than 12 megapixels.")
            if getattr(image, "n_frames", 1) != 1 or image.mode not in ("L", "RGB"):
                raise InvalidImage("Save a single frame as RGB or grayscale and remove any transparency.")
            return ImageOps.exif_transpose(image).convert("RGB")
    except (OSError, SyntaxError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise InvalidImage("Couldn’t open that image. Try saving it as a PNG or JPEG.") from exc


def coordinates(values):
    if not isinstance(values, list) or len(values) != 4:
        raise InvalidImage("Mark both ends of the bar and two opposite corners of the cell box.")
    if any(type(v) is not int or not 0 <= v <= MAX_PIXELS for v in values):
        raise InvalidImage("Use whole numbers for the pixel coordinates, starting at zero.")
    return values

