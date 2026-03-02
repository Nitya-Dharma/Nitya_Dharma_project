"""
Security utilities for input validation and sanitization.

This module provides functions to prevent injection attacks.
"""

import json
from django.core.exceptions import ValidationError


# NoSQL injection operators to block
NOSQL_OPERATORS = [
    '$ne', '$gt', '$lt', '$gte', '$lte', '$in', '$nin',
    '$where', '$regex', '$or', '$and', '$not', '$nor',
    '$exists', '$type', '$mod', '$size', '$all', '$elemMatch'
]


def validate_json_payload(payload, allowed_fields=None):
    """
    Validate JSON payload to prevent NoSQL injection.
    
    Args:
        payload: Dictionary from parsed JSON
        allowed_fields: Optional list of allowed field names. If None, only blocks operators.
    
    Returns:
        Validated payload dictionary
    
    Raises:
        ValidationError: If payload contains NoSQL operators or disallowed fields
    """
    if not isinstance(payload, dict):
        raise ValidationError("Payload must be a dictionary")
    
    validated = {}
    
    for key, value in payload.items():
        # Block NoSQL operators
        if key.startswith('$') or any(op in key for op in NOSQL_OPERATORS):
            raise ValidationError(f"NoSQL operators not allowed: {key}")
        
        # Block nested dictionaries that could contain operators
        if isinstance(value, dict):
            # Recursively validate nested dictionaries
            for nested_key in value.keys():
                if nested_key.startswith('$') or any(op in nested_key for op in NOSQL_OPERATORS):
                    raise ValidationError(f"NoSQL operators not allowed in nested object: {nested_key}")
            # If nested dict is allowed, validate it recursively
            validated[key] = validate_json_payload(value, allowed_fields=None)
        elif isinstance(value, list):
            # Validate list items
            validated_list = []
            for item in value:
                if isinstance(item, dict):
                    validated_list.append(validate_json_payload(item, allowed_fields=None))
                else:
                    validated_list.append(item)
            validated[key] = validated_list
        else:
            validated[key] = value
        
        # If allowed_fields specified, check field is whitelisted
        if allowed_fields is not None and key not in allowed_fields:
            raise ValidationError(f"Field not allowed: {key}")
    
    return validated


def safe_json_loads(request_body, allowed_fields=None):
    """
    Safely parse and validate JSON request body.
    
    Args:
        request_body: Raw request body (bytes)
        allowed_fields: Optional list of allowed field names
    
    Returns:
        Validated dictionary
    
    Raises:
        json.JSONDecodeError: If JSON is invalid
        ValidationError: If payload contains NoSQL operators or disallowed fields
    """
    if not request_body:
        return {}
    
    # Parse JSON
    try:
        data = json.loads(request_body)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON: {str(e)}", e.doc, e.pos)
    
    # Validate payload
    if isinstance(data, dict):
        return validate_json_payload(data, allowed_fields)
    else:
        raise ValidationError("JSON payload must be an object (dictionary)")




















