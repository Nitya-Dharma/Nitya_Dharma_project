"""
Production image optimization pipeline (re-exports from image_pipeline).

Use core.image_pipeline for full pipeline (WebP + responsive).
This module keeps backward compatibility for optimize_image_if_new.
"""
from core.image_pipeline import (
    optimize_image,
    optimize_image_if_new,
    process_derived_images_after_save,
)

__all__ = ['optimize_image', 'optimize_image_if_new', 'process_derived_images_after_save']
