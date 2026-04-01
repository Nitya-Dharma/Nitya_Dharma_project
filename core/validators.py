import os

from django.core.exceptions import ValidationError


ALLOWED_IMAGE_TYPES = [
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/svg+xml",
]

ALLOWED_IMAGE_EXTENSIONS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".svg",
]


def validate_image_file(file):
    content_type = getattr(file, "content_type", None)
    if content_type and content_type not in ALLOWED_IMAGE_TYPES:
        raise ValidationError(
            f"Unsupported image format: {content_type}. Allowed: JPEG, PNG, WEBP, GIF, SVG"
        )


def validate_image_extension(file):
    ext = os.path.splitext(getattr(file, "name", "") or "")[1].lower()
    if ext and ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(f"Unsupported file extension: {ext}")
