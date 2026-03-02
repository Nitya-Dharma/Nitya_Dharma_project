"""
Referral code generator for Admin Pandit referral links.

Generates non-sequential, non-guessable referral codes in format:
REF-AP-XXXXXX (8-12 characters, A-Z, 0-9)
"""

import random
import string


def generate_referral_code() -> str:
    """
    Generate a unique referral code.
    
    Format: REF-AP-XXXXXX
    - Prefix: REF-AP- (7 chars)
    - Random suffix: 6-10 alphanumeric chars (A-Z, 0-9)
    - Total: 13-17 chars (but we'll use 8-12 as per spec, so format: REF-AP-XXX)
    
    Actually, let's use format: REF-AP-XXXXXX (13 chars total)
    But spec says 8-12, so let's use: REF-AP-XXX (10 chars) or REF-AP-XXXX (11 chars)
    
    Let's use: REF-AP-XXXX (11 chars) - fits in 8-12 range
    
    Returns:
        str: Referral code (e.g., "REF-AP-9XK2M7")
    """
    # Generate random suffix (4 chars: A-Z, 0-9)
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"REF-AP-{suffix}"


def generate_unique_referral_code(model_class, max_attempts=100) -> str:
    """
    Generate a unique referral code that doesn't exist in the database.
    
    Args:
        model_class: The ReferralLink model class
        max_attempts: Maximum attempts to generate unique code
        
    Returns:
        str: Unique referral code
        
    Raises:
        RuntimeError: If unable to generate unique code after max_attempts
    """
    for _ in range(max_attempts):
        code = generate_referral_code()
        if not model_class.objects.filter(code=code).exists():
            return code
    
    raise RuntimeError(f"Unable to generate unique referral code after {max_attempts} attempts")






















