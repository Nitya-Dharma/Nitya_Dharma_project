"""
Full production image pipeline: compression, resize, WebP, responsive sizes.

- Optimizes uploads (resize max 2000px, JPEG 85 / PNG optimize, strip metadata).
- Preserves transparency (PNG when needed).
- Generates WebP version and responsive sizes (300, 600, 1200, 2000, thumb 300)
  as separate files in the same directory (no DB changes).
- Integrates via optimize_image_if_new() before save and
  process_derived_images_after_save() after save.
"""
import logging
import os
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile, UploadedFile

logger = logging.getLogger(__name__)

# Lazy Pillow import
def _get_pillow_image():
    from PIL import Image
    return Image

# Resize and quality
MAX_WIDTH = 2000
JPEG_QUALITY = 85
PNG_COMPRESSION = 6
WEBP_QUALITY = 80
WEBP_METHOD = 6

# Responsive widths (px); thumb for listings
RESPONSIVE_WIDTHS = (300, 600, 1200, 2000)
THUMB_WIDTH = 300


def _is_new_upload(file):
    if file is None:
        return False
    return isinstance(file, UploadedFile)


def optimize_image(uploaded_image):
    """
    Optimize upload: resize if > MAX_WIDTH, compress, strip metadata.
    Preserve transparency (PNG); otherwise JPEG quality 85.
    Returns InMemoryUploadedFile.
    """
    Image = _get_pillow_image()
    uploaded_image.seek(0)
    image = Image.open(uploaded_image)
    image.load()
    image = image.copy()

    if image.width > MAX_WIDTH:
        ratio = MAX_WIDTH / float(image.width)
        new_height = int(image.height * ratio)
        image = image.resize((MAX_WIDTH, new_height), Image.Resampling.LANCZOS)

    output = BytesIO()
    original_name = getattr(uploaded_image, 'name', 'image.jpg') or 'image.jpg'
    has_alpha = image.mode in ('RGBA', 'LA') or (
        image.mode == 'P' and 'transparency' in image.info
    )

    if has_alpha:
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        image.save(output, format='PNG', optimize=True, compress_level=PNG_COMPRESSION)
        content_type = 'image/png'
        name = original_name.rsplit('.', 1)[0] + '.png' if '.' in original_name else original_name + '.png'
    else:
        if image.mode in ('RGBA', 'P', 'LA'):
            image = image.convert('RGB')
        image.save(output, format='JPEG', quality=JPEG_QUALITY, optimize=True)
        content_type = 'image/jpeg'
        name = original_name.rsplit('.', 1)[0] + '.jpg' if '.' in original_name else original_name + '.jpg'

    output.seek(0)
    size = output.getbuffer().nbytes
    return InMemoryUploadedFile(output, 'ImageField', name, content_type, size, None)


def _pil_to_webp(image, quality=WEBP_QUALITY, method=WEBP_METHOD):
    """Return bytes of image as WebP. Preserves alpha if present."""
    out = BytesIO()
    if image.mode in ('RGBA', 'LA', 'P'):
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        image.save(out, format='WEBP', quality=quality, method=method, lossless=False)
    else:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        image.save(out, format='WEBP', quality=quality, method=method)
    out.seek(0)
    return out.getvalue()


def _pil_to_jpeg_or_png(image, width, has_alpha):
    """Resize to width (aspect ratio), return (bytes, ext)."""
    Image = _get_pillow_image()
    if image.width <= width:
        w, h = image.width, image.height
    else:
        ratio = width / float(image.width)
        h = int(image.height * ratio)
        w = width
    resized = image.resize((w, h), Image.Resampling.LANCZOS)
    out = BytesIO()
    if has_alpha:
        if resized.mode != 'RGBA':
            resized = resized.convert('RGBA')
        resized.save(out, format='PNG', optimize=True, compress_level=PNG_COMPRESSION)
        return out.getvalue(), '.png'
    else:
        if resized.mode != 'RGB':
            resized = resized.convert('RGB')
        resized.save(out, format='JPEG', quality=JPEG_QUALITY, optimize=True)
        return out.getvalue(), '.jpg'


def generate_webp_version(image_or_path, storage, dir_path, base_name, ext):
    """
    Write a WebP file alongside the main image.
    image_or_path: PIL Image or path string to open.
    storage: Django storage instance.
    dir_path: directory path (e.g. 'profiles/pandit_images').
    base_name: filename without extension.
    ext: main file extension (e.g. '.jpg') for logging only.
    """
    try:
        Image = _get_pillow_image()
        if hasattr(image_or_path, 'width'):
            image = image_or_path
        else:
            with storage.open(image_or_path, 'rb') as f:
                image = Image.open(f).copy()
                image.load()
        webp_data = _pil_to_webp(image)
        webp_path = os.path.join(dir_path, base_name + '.webp')
        storage.save(webp_path, ContentFile(webp_data))
    except Exception as e:
        logger.warning("WebP generation failed for %s: %s", base_name + ext, e)


def generate_responsive_sizes(image, storage, dir_path, base_name, ext, has_alpha):
    """
    Write responsive and thumbnail files: base_300.ext, base_600.ext, base_1200.ext,
    base_2000.ext, base_thumb.ext (300px). Same format as main (jpg or png).
    """
    try:
        for width in RESPONSIVE_WIDTHS:
            data, suffix = _pil_to_jpeg_or_png(image, width, has_alpha)
            name = f"{base_name}_{width}{suffix}"
            storage.save(os.path.join(dir_path, name), ContentFile(data))
        # Thumbnail (300px, same as first responsive)
        data_thumb, suffix = _pil_to_jpeg_or_png(image, THUMB_WIDTH, has_alpha)
        storage.save(os.path.join(dir_path, f"{base_name}_thumb{suffix}"), ContentFile(data_thumb))
    except Exception as e:
        logger.warning("Responsive sizes generation failed for %s: %s", base_name + ext, e)


def optimize_image_if_new(instance, field_name):
    """
    If field holds a new upload, replace with optimized file and mark for derived generation.
    Call before super().save(). Sets instance._image_pipeline_derived_pending (set of field names).
    """
    file = getattr(instance, field_name, None)
    if not _is_new_upload(file):
        return
    try:
        setattr(instance, field_name, optimize_image(file))
        pending = getattr(instance, '_image_pipeline_derived_pending', None)
        if pending is None:
            instance._image_pipeline_derived_pending = set()
        instance._image_pipeline_derived_pending.add(field_name)
    except Exception as e:
        logger.warning("Image optimization failed for %s.%s: %s", type(instance).__name__, field_name, e)


def process_derived_images_after_save(instance, field_name):
    """
    After super().save(), generate WebP and responsive sizes for the given field
    if it was a new upload. Call after super().save().
    """
    pending = getattr(instance, '_image_pipeline_derived_pending', None)
    if not pending or field_name not in pending:
        return
    field = getattr(instance, field_name, None)
    if not field or not field.name:
        pending.discard(field_name)
        return
    try:
        storage = field.storage
        dir_path = os.path.dirname(field.name)
        base_ext = os.path.splitext(os.path.basename(field.name))[1].lower()
        base_name = os.path.splitext(os.path.basename(field.name))[0]

        Image = _get_pillow_image()
        with storage.open(field.name, 'rb') as f:
            image = Image.open(f).copy()
            image.load()
        has_alpha = image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info)

        generate_webp_version(image, storage, dir_path, base_name, base_ext)
        generate_responsive_sizes(image, storage, dir_path, base_name, base_ext, has_alpha)
    except Exception as e:
        logger.warning("Derived images failed for %s.%s: %s", type(instance).__name__, field_name, e)
    finally:
        pending.discard(field_name)
