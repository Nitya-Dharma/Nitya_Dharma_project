"""
Feature Flags — PART 6 — PRE-LAUNCH & DEPLOYMENT READINESS

TASK 6.4: Feature Flag Guardrails

Add feature flags for risky flows.

RULES:
- Flags default OFF
- Flags server-side only
- No UI-only flags

VERIFY:
- Feature can be disabled instantly
"""

import os
from django.conf import settings
from typing import Dict, Any


# Feature flags configuration
# All flags default to False (OFF)
FEATURE_FLAGS = {
    # New dashboards
    'ENABLE_NEW_DASHBOARD': False,
    
    # New page types
    'ENABLE_BRAND_PAGES': False,
    'ENABLE_SERVICE_PAGES': False,
    
    # New moderation UI
    'ENABLE_NEW_MODERATION_UI': False,
    
    # New engagement triggers
    'ENABLE_NEW_ENGAGEMENT_TRIGGERS': False,
    
    # Experimental features
    'ENABLE_EXPERIMENTAL_SEARCH': False,
    'ENABLE_EXPERIMENTAL_BOOKING': False,
}


def get_feature_flag(flag_name: str, default: bool = False) -> bool:
    """
    Get feature flag value.
    
    Args:
        flag_name: Name of feature flag
        default: Default value if flag not found
    
    Returns:
        bool: Feature flag value
    """
    # Check environment variable first (highest priority)
    env_value = os.environ.get(f'FEATURE_FLAG_{flag_name.upper()}')
    if env_value is not None:
        return env_value.lower() in ('true', '1', 'yes', 'on')
    
    # Check settings
    if hasattr(settings, 'FEATURE_FLAGS'):
        return settings.FEATURE_FLAGS.get(flag_name, default)
    
    # Check default flags
    return FEATURE_FLAGS.get(flag_name, default)


def is_feature_enabled(flag_name: str) -> bool:
    """
    Check if a feature is enabled.
    
    Args:
        flag_name: Name of feature flag
    
    Returns:
        bool: True if feature is enabled
    """
    return get_feature_flag(flag_name, default=False)


def get_all_feature_flags() -> Dict[str, bool]:
    """
    Get all feature flags.
    
    Returns:
        Dict mapping flag names to values
    """
    flags = {}
    for flag_name in FEATURE_FLAGS.keys():
        flags[flag_name] = get_feature_flag(flag_name)
    return flags


# Context processor for templates
def feature_flags_context(request):
    """
    Add feature flags to template context.
    
    Usage in settings.py:
        TEMPLATES = [
            {
                'OPTIONS': {
                    'context_processors': [
                        ...
                        'core.feature_flags.feature_flags_context',
                    ],
                },
            },
        ]
    """
    return {
        'feature_flags': get_all_feature_flags(),
    }

