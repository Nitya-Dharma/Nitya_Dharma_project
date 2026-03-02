"""
File Upload Security Utilities (PART 4 Fix)

Centralized validation for all file uploads to prevent:
- Stored XSS
- Malware hosting
- Polyglot file abuse
- RCE via malicious uploads

This module provides allowlist-based validation (not blocklist).
"""

import os
import re
from django.conf import settings
from django.core.exceptions import ValidationError
from pathlib import Path


# Extension Allowlists (PART 4: Use allowlist, not blocklist)
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.csv'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS

# MIME Type Allowlists (PART 4: Validate MIME type, not just extension)
ALLOWED_IMAGE_MIME_TYPES = {
    'image/jpeg',
    'image/jpg',
    'image/png',
    'image/gif',
    'image/webp',
}

ALLOWED_DOCUMENT_MIME_TYPES = {
    'application/pdf',
    'text/csv',
    'text/plain',  # CSV files may be detected as text/plain
}

ALLOWED_MIME_TYPES = ALLOWED_IMAGE_MIME_TYPES | ALLOWED_DOCUMENT_MIME_TYPES

# Maximum file sizes (in bytes); overridable via settings, defaults preserved
_DEFAULT_MAX_IMAGE = 10 * 1024 * 1024   # 10 MB
_DEFAULT_MAX_DOCUMENT = 50 * 1024 * 1024  # 50 MB
_DEFAULT_MAX_CSV = 5 * 1024 * 1024   # 5 MB
MAX_IMAGE_SIZE = getattr(settings, 'FILE_UPLOAD_MAX_IMAGE_BYTES', _DEFAULT_MAX_IMAGE)
MAX_DOCUMENT_SIZE = getattr(settings, 'FILE_UPLOAD_MAX_DOCUMENT_BYTES', _DEFAULT_MAX_DOCUMENT)
MAX_CSV_SIZE = getattr(settings, 'FILE_UPLOAD_MAX_CSV_BYTES', _DEFAULT_MAX_CSV)

# Dangerous extensions that must be blocked (for reference - we use allowlist)
DANGEROUS_EXTENSIONS = {'.php', '.jsp', '.asp', '.exe', '.sh', '.bat', '.cmd', '.js', '.html', '.svg', '.xml'}


def get_file_extension(filename):
    """
    Safely extract file extension from filename.
    
    Args:
        filename: Original filename
        
    Returns:
        Lowercase extension with leading dot (e.g., '.jpg')
    """
    if not filename:
        return None
    
    # Get extension
    ext = Path(filename).suffix.lower()
    
    # Ensure it starts with dot
    if ext and not ext.startswith('.'):
        ext = '.' + ext
    
    return ext


def sanitize_filename(filename):
    """
    Sanitize filename to prevent path traversal and special characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for storage
    """
    if not filename:
        raise ValidationError("Filename is required")
    
    # Get base name (remove path components)
    base_name = os.path.basename(filename)
    
    # Remove any path traversal attempts
    if '..' in base_name or '/' in base_name or '\\' in base_name:
        raise ValidationError("Invalid filename: path traversal detected")
    
    # Remove dangerous characters
    sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', base_name)
    
    # Ensure it's not empty
    if not sanitized or sanitized == '.' or sanitized == '..':
        raise ValidationError("Invalid filename")
    
    return sanitized


def validate_uploaded_file(file, allowed_extensions=None, allowed_mime_types=None, max_size=None, file_type='image'):
    """
    Validate uploaded file for security (PART 4 fix).
    
    This function enforces:
    - Extension allowlist (not blocklist)
    - MIME type validation
    - Filename sanitization
    - Size limits
    - Double extension detection
    
    Args:
        file: Django UploadedFile object
        allowed_extensions: Optional set of allowed extensions (defaults based on file_type)
        allowed_mime_types: Optional set of allowed MIME types (defaults based on file_type)
        max_size: Optional maximum file size in bytes (defaults based on file_type)
        file_type: 'image', 'document', or 'csv' (determines defaults)
        
    Returns:
        Tuple (sanitized_filename, validated_file)
        
    Raises:
        ValidationError: If file fails validation
    """
    if not file:
        raise ValidationError("No file provided")
    
    # Set defaults based on file type
    if allowed_extensions is None:
        if file_type == 'image':
            allowed_extensions = ALLOWED_IMAGE_EXTENSIONS
        elif file_type == 'csv':
            allowed_extensions = {'.csv'}
        else:
            allowed_extensions = ALLOWED_DOCUMENT_EXTENSIONS
    
    if allowed_mime_types is None:
        if file_type == 'image':
            allowed_mime_types = ALLOWED_IMAGE_MIME_TYPES
        elif file_type == 'csv':
            allowed_mime_types = ALLOWED_DOCUMENT_MIME_TYPES | {'text/csv', 'text/plain'}
        else:
            allowed_mime_types = ALLOWED_DOCUMENT_MIME_TYPES
    
    if max_size is None:
        if file_type == 'image':
            max_size = MAX_IMAGE_SIZE
        elif file_type == 'csv':
            max_size = MAX_CSV_SIZE
        else:
            max_size = MAX_DOCUMENT_SIZE
    
    # Get original filename
    original_filename = file.name if hasattr(file, 'name') else str(file)
    
    # Sanitize filename
    sanitized_filename = sanitize_filename(original_filename)
    
    # Extract extension
    ext = get_file_extension(sanitized_filename)
    
    if not ext:
        raise ValidationError("File must have an extension")
    
    # PART 4: Check for double extensions (e.g., image.jpg.php)
    if sanitized_filename.count('.') > 1:
        # Get last extension only
        parts = sanitized_filename.rsplit('.', 1)
        if len(parts) == 2:
            last_ext = '.' + parts[1].lower()
            if last_ext not in allowed_extensions:
                raise ValidationError(f"Double extension detected or invalid extension: {last_ext}")
            ext = last_ext
    
    # PART 4: Extension allowlist check (not blocklist)
    if ext not in allowed_extensions:
        raise ValidationError(
            f"File type not allowed. Allowed extensions: {', '.join(sorted(allowed_extensions))}"
        )
    
    # PART 4: MIME type validation
    content_type = file.content_type if hasattr(file, 'content_type') else None
    
    if content_type:
        # Normalize MIME type (remove charset, etc.)
        mime_type = content_type.split(';')[0].strip().lower()
        
        if mime_type not in allowed_mime_types:
            raise ValidationError(
                f"MIME type not allowed: {content_type}. Allowed types: {', '.join(sorted(allowed_mime_types))}"
            )
    
    # PART 4: Size validation
    if hasattr(file, 'size'):
        file_size = file.size
    else:
        # Fallback: read file to get size
        file.seek(0)
        content = file.read()
        file_size = len(content)
        file.seek(0)  # Reset file pointer
    
    if file_size > max_size:
        size_mb = max_size / (1024 * 1024)
        raise ValidationError(f"File size exceeds maximum allowed size of {size_mb:.1f} MB")
    
    # Additional security: Check filename doesn't contain dangerous patterns
    filename_lower = sanitized_filename.lower()
    for dangerous in DANGEROUS_EXTENSIONS:
        if dangerous in filename_lower:
            raise ValidationError(f"Dangerous file type detected: {dangerous}")
    
    return sanitized_filename, file


def validate_image_upload(file):
    """
    Convenience function for image uploads.
    
    Args:
        file: Django UploadedFile object
        
    Returns:
        Tuple (sanitized_filename, validated_file)
    """
    return validate_uploaded_file(file, file_type='image')


def validate_csv_upload(file):
    """
    Convenience function for CSV uploads.
    
    Args:
        file: Django UploadedFile object
        
    Returns:
        Tuple (sanitized_filename, validated_file)
    """
    return validate_uploaded_file(file, file_type='csv')


def validate_document_upload(file):
    """
    Convenience function for document uploads.
    
    Args:
        file: Django UploadedFile object
        
    Returns:
        Tuple (sanitized_filename, validated_file)
    """
    return validate_uploaded_file(file, file_type='document')

