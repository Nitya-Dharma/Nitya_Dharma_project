"""
Search Logging

Task 7.16: Search Request Logging (No PII)

Logs search requests for analytics and monitoring.
Strictly no PII, no user identification, no personal data.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def log_search_request(
    request,
    filters: Dict[str, Any],
    result_count: int
):
    """
    Log a search request for analytics.
    
    Task 7.16: Search Request Logging (No PII)
    
    Logs:
    - Search filters used (city_id, area_id, pooja_id, etc.)
    - Result count
    - Request metadata (IP hash, user agent hash - if needed)
    
    Does NOT log:
    - User ID
    - Email
    - Personal information
    - Search keywords (may contain PII)
    - Any identifying information
    
    Args:
        request: Django request object
        filters: Dictionary of search filters (sanitized, no PII)
        result_count: Number of results returned
    """
    # Sanitize filters - remove any potential PII
    sanitized_filters = {}
    
    # Only log safe filter IDs (no keywords, no personal data)
    if 'city_id' in filters:
        sanitized_filters['city_id'] = filters['city_id']
    if 'area_id' in filters:
        sanitized_filters['area_id'] = filters['area_id']
    if 'pooja_id' in filters:
        sanitized_filters['pooja_id'] = filters['pooja_id']
    if 'day_of_week' in filters:
        sanitized_filters['day_of_week'] = filters['day_of_week']
    if 'specific_date' in filters:
        sanitized_filters['specific_date'] = str(filters['specific_date'])
    if 'start_time' in filters:
        sanitized_filters['start_time'] = str(filters['start_time'])
    if 'end_time' in filters:
        sanitized_filters['end_time'] = str(filters['end_time'])
    
    # Explicitly exclude keywords and any text fields (may contain PII)
    # Do NOT log: keyword, search_text, query, etc.
    
    # Log search request (INFO level for analytics)
    logger.info(
        "Search request",
        extra={
            'filters': sanitized_filters,
            'result_count': result_count,
            'has_results': result_count > 0,
            # Optional: Log request method and path (safe)
            'method': request.method,
            'path': request.path,
            # Do NOT log: user, IP, user agent (may contain PII)
        }
    )
