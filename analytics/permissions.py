"""
Analytics Access Control & Permissions

Enforces access control for analytics data.
Only authorized roles can access analytics.
"""

from accounts.utils import is_admin


class CanAccessAnalytics:
    """
    Helper class for checking analytics access.
    """
    
    @staticmethod
    def can_access(user) -> bool:
        """
        Check if a user can access analytics.
        
        Args:
            user: User instance
            
        Returns:
            bool: True if user can access analytics
        """
        if not user or not user.is_authenticated:
            return False
        
        return is_admin(user)
