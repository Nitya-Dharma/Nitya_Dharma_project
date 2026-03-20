"""
Automatic crop and resize for advertisement images.

Generates correctly sized images for each ad position from a single upload.
Uses Pillow; runs only on save/upload (not during page render).
"""

import logging
import uuid
from io import BytesIO

from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

# Allowed formats for ad images (PIL format names and file extensions)
ALLOWED_PIL_FORMATS = {"JPEG", "PNG", "WEBP", "JFIF"}
ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")

# Output quality
JPEG_QUALITY = 88
PNG_COMPRESSION = 6
WEBP_QUALITY = 85


def _get_pillow_image():
    from PIL import Image
    return Image


def _open_image(source):
    """
    Load a PIL Image from source.
    source: path string, or file-like with .read()/.seek(0), or Django File/FieldFile.
    """
    Image = _get_pillow_image()
    if hasattr(source, "read"):
        if hasattr(source, "seek"):
            source.seek(0)
        return Image.open(source).copy()
    if isinstance(source, str):
        with open(source, "rb") as f:
            return Image.open(f).copy()
    if hasattr(source, "path"):
        with open(source.path, "rb") as f:
            return Image.open(f).copy()
    raise TypeError("source must be path string, file-like, or Django File with .path")


def _validate_format(image):
    """Raise ValueError if image format is not allowed (JPEG, PNG, WEBP)."""
    fmt = (getattr(image, "format", None) or "").upper()
    if fmt and fmt not in ALLOWED_PIL_FORMATS:
        raise ValueError(f"Unsupported image format: {fmt}. Allowed: JPEG, PNG, WEBP.")


def process_ad_image(source, target_width, target_height, output_filename=None):
    """
    Crop (center) and resize the image to exact target dimensions.

    - Loads the image with Pillow.
    - Crops to the target aspect ratio (center crop) to avoid distortion.
    - Resizes to exactly (target_width, target_height).
    - Returns a ContentFile suitable for saving to an ImageField.

    Args:
        source: Path string, file-like object, or Django File/FieldFile.
        target_width: int, target width in pixels.
        target_height: int, target height in pixels.
        output_filename: optional str; if not provided, a name is generated.

    Returns:
        django.core.files.base.ContentFile with .name set.

    Raises:
        ValueError: If the image format is not JPEG, PNG, or WEBP.
    """
    Image = _get_pillow_image()
    image = _open_image(source)
    image.load()
    _validate_format(image)

    w, h = image.width, image.height
    target_ratio = target_width / float(target_height)
    current_ratio = w / float(h)

    if current_ratio > target_ratio:
        # Crop width: take center
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        image = image.crop((left, 0, left + new_w, h))
    elif current_ratio < target_ratio:
        # Crop height: take center
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        image = image.crop((0, top, w, top + new_h))

    image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)

    has_alpha = image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    )
    out = BytesIO()
    if has_alpha:
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        image.save(out, format="PNG", optimize=True, compress_level=PNG_COMPRESSION)
        ext = ".png"
        content_type = "image/png"
    else:
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        ext = ".jpg"
        content_type = "image/jpeg"

    out.seek(0)
    data = out.getvalue()
    name = output_filename or f"processed_{target_width}x{target_height}_{uuid.uuid4().hex[:8]}{ext}"
    if not name.lower().endswith(ext):
        name = name.rsplit(".", 1)[0] + ext if "." in name else name + ext

    return ContentFile(data, name=name)
