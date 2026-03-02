"""
Public ID utility module for generating and managing public-facing IDs.

This module provides:
- UUIDv7 generation (time-ordered, non-guessable)
- Public ID resolution utilities
- Security validation functions

Architecture:
- Internal IDs: BIGINT (primary keys, for joins)
- Public IDs: UUIDv7 (for URLs, APIs, frontend)
"""

import uuid
from typing import Optional, Type, TypeVar
from django.db import models
from django.core.exceptions import ValidationError

# Python 3.13+ has uuid.uuid7, fallback for older versions
try:
    from uuid import uuid7
except ImportError:
    # Fallback: Use uuid4 for older Python versions
    # Note: uuid4 is not time-ordered, but works as fallback
    import uuid as uuid_module
    uuid7 = uuid_module.uuid4


def generate_public_id() -> str:
    """
    Generate a UUIDv7 public ID.
    
    UUIDv7 is time-ordered and non-guessable, perfect for public-facing IDs.
    
    Returns:
        str: UUIDv7 string (e.g., "018f1234-5678-7890-abcd-ef1234567890")
    """
    return str(uuid7())


def validate_public_id(value: str) -> None:
    """
    Validate that a value is a valid UUID format.
    
    Args:
        value: The value to validate
        
    Raises:
        ValidationError: If value is not a valid UUID
    """
    try:
        uuid.UUID(value)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid public ID format: {value}")


# Type variable for model classes
ModelType = TypeVar('ModelType', bound=models.Model)


def resolve_public_id(
    model_class: Type[ModelType],
    public_id: str,
    field_name: str = 'public_id'
) -> Optional[ModelType]:
    """
    Resolve a public_id to an internal model instance.
    
    Security:
    - Returns None (not raises) for invalid IDs
    - Prevents information leakage
    - Use get_object_or_404 in views for proper 404 handling
    
    Args:
        model_class: The Django model class
        public_id: The public ID to resolve
        field_name: The field name containing public_id (default: 'public_id')
        
    Returns:
        Model instance or None if not found
    """
    try:
        validate_public_id(public_id)
        return model_class.objects.get(**{field_name: public_id})
    except (model_class.DoesNotExist, ValidationError):
        return None


def get_internal_id_from_public(
    model_class: Type[ModelType],
    public_id: str,
    field_name: str = 'public_id'
) -> Optional[int]:
    """
    Get internal BIGINT ID from public_id.
    
    Used internally for joins and queries.
    Never expose this to frontend.
    
    Args:
        model_class: The Django model class
        public_id: The public ID
        field_name: The field name containing public_id
        
    Returns:
        Internal ID (int) or None if not found
    """
    instance = resolve_public_id(model_class, public_id, field_name)
    return instance.id if instance else None


def reject_bigint_id(value: str) -> bool:
    """
    Check if a value looks like a BIGINT ID (numeric only).
    
    Security: Reject any request containing BIGINT IDs in URLs/APIs.
    
    Args:
        value: The value to check
        
    Returns:
        True if value looks like a BIGINT ID (should be rejected)
    """
    if not value:
        return False
    # Check if value is purely numeric (likely a BIGINT ID)
    # UUIDs contain hyphens and letters, so numeric-only = BIGINT
    return value.isdigit() and len(value) < 20  # UUIDs are 36 chars

