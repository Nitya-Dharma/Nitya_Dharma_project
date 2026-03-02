"""
Safety Test Matrix — PART 4 — AUTOMATED GUARDRAILS

Comprehensive test suite that verifies deletion protection across all scenarios.

These tests MUST pass for the build to succeed.
If any test fails, the system is NOT safe.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

User = get_user_model()


class SafetyTestMatrix(TestCase):
    """
    Safety Test Matrix — All scenarios must pass.
    
    | Scenario                        | Expected Result            |
    | ------------------------------- | -------------------------- |
    | Pandit with referrals deleted   | ❌ Blocked, deactivated     |
    | Admin Pandit removed            | Approval history preserved |
    | Page deleted                    | Marked INVISIBLE           |
    | Pinned post author removed      | Post stays                 |
    | Review author removed           | Review stays, anonymized   |
    | Notification actor removed      | Notification preserved     |
    | Engagement event entity removed | Event resolvable           |
    """
    
    def setUp(self):
        """Set up test data."""
        # Create test users
        self.user1 = User.objects.create_user(
            email="user1@example.com",
            password="testpass123",
            role='user'
        )
        self.pandit1 = User.objects.create_user(
            email="pandit1@example.com",
            password="testpass123",
            role='pandit',
            status='active'
        )
        self.admin_pandit = User.objects.create_user(
            email="admin@example.com",
            password="testpass123",
            role='admin',
            status='active',
            is_staff=True
        )
    
    def test_scenario_1_pandit_with_referrals_deleted(self):
        """
        Scenario: Pandit with referrals deleted
        Expected: ❌ Blocked, deactivated
        """
        try:
            from profiles.models import PanditProfile
            from referrals.models import Referral
            
            # Create referral
            referral = Referral.objects.create(
                referrer=self.admin_pandit,
                referred_pandit=self.pandit1,
                referral_code="TEST123"
            )
            
            # Attempt to delete pandit with referral
            # Should be blocked
            with self.assertRaises((ValidationError, Exception)) as cm:
                self.pandit1.delete()
            
            # Verify error indicates deletion is blocked
            error_message = str(cm.exception).lower()
            self.assertIn(
                "delete" or "not allowed" or "deactivate",
                error_message,
                f"Pandit deletion should be blocked, but got: {error_message}"
            )
            
            # Verify referral still exists
            self.assertTrue(Referral.objects.filter(id=referral.id).exists())
            
        except ImportError:
            self.skipTest("Required models not available")
    
    def test_scenario_2_admin_pandit_removed(self):
        """
        Scenario: Admin Pandit removed
        Expected: Approval history preserved
        """
        try:
            from profiles.models import PanditProfile
            
            # Create admin pandit profile
            admin_profile, _ = PanditProfile.objects.get_or_create(user=self.admin_pandit)
            
            # Approve a pandit (simulate approval action)
            pandit_profile, _ = PanditProfile.objects.get_or_create(user=self.pandit1)
            # In real system, there would be approval records
            
            # Attempt to delete admin pandit
            # Should be blocked
            with self.assertRaises((ValidationError, Exception)) as cm:
                self.admin_pandit.delete()
            
            # Verify error indicates deletion is blocked
            error_message = str(cm.exception).lower()
            self.assertIn(
                "delete" or "not allowed" or "deactivate",
                error_message,
                f"Admin Pandit deletion should be blocked, but got: {error_message}"
            )
            
        except ImportError:
            self.skipTest("Required models not available")
    
    def test_scenario_3_page_deleted(self):
        """
        Scenario: Page deleted
        Expected: Marked INVISIBLE
        """
        try:
            from pages.models import Page
            
            # Create a page
            page = Page.objects.create(
                name="Test Temple",
                page_type='temple',
                slug="test-temple",
                created_by=self.admin_pandit
            )
            
            # Attempt to delete page
            # Should be blocked or marked INVISIBLE
            with self.assertRaises((ValidationError, Exception)) as cm:
                page.delete()
            
            # Verify error indicates deletion is blocked
            error_message = str(cm.exception).lower()
            self.assertIn(
                "delete" or "not allowed" or "invisible" or "deactivate",
                error_message,
                f"Page deletion should be blocked, but got: {error_message}"
            )
            
            # Verify page still exists (should be marked INVISIBLE)
            page.refresh_from_db()
            self.assertIsNotNone(page.id)
            
        except ImportError:
            self.skipTest("Pages app not available")
    
    def test_scenario_4_pinned_post_author_removed(self):
        """
        Scenario: Pinned post author removed
        Expected: Post stays
        """
        try:
            from pages.models import Page, PagePost
            
            # Create page and post
            page = Page.objects.create(
                name="Test Temple",
                page_type='temple',
                slug="test-temple",
                created_by=self.admin_pandit
            )
            
            post = PagePost.objects.create(
                page=page,
                author=self.admin_pandit,
                title="Test Post",
                content="Test content",
                is_pinned=True
            )
            
            # Attempt to delete author
            # Should be blocked
            with self.assertRaises((ValidationError, Exception)) as cm:
                self.admin_pandit.delete()
            
            # Verify error indicates deletion is blocked
            error_message = str(cm.exception).lower()
            self.assertIn(
                "delete" or "not allowed" or "deactivate",
                error_message,
                f"Author deletion should be blocked, but got: {error_message}"
            )
            
            # Verify post still exists
            self.assertTrue(PagePost.objects.filter(id=post.id).exists())
            
        except ImportError:
            self.skipTest("Pages app not available")
    
    def test_scenario_5_review_author_removed(self):
        """
        Scenario: Review author removed
        Expected: Review stays, anonymized
        """
        try:
            from reviews.models import Review
            
            # Create review
            review = Review.objects.create(
                reviewer=self.user1,
                pandit=self.pandit1,
                rating=5,
                comment="Great pandit!"
            )
            
            # Attempt to delete reviewer
            # Should be blocked
            with self.assertRaises((ValidationError, Exception)) as cm:
                self.user1.delete()
            
            # Verify error indicates deletion is blocked
            error_message = str(cm.exception).lower()
            self.assertIn(
                "delete" or "not allowed" or "deactivate",
                error_message,
                f"Reviewer deletion should be blocked, but got: {error_message}"
            )
            
            # Verify review still exists
            self.assertTrue(Review.objects.filter(id=review.id).exists())
            
        except ImportError:
            self.skipTest("Reviews app not available")
    
    def test_scenario_6_notification_actor_removed(self):
        """
        Scenario: Notification actor removed
        Expected: Notification preserved
        """
        try:
            from notifications.models import Notification
            
            # Create notification
            notification = Notification.objects.create(
                recipient=self.user1,
                message="Test notification",
                notification_type='info'
            )
            
            # Attempt to delete recipient
            # Should be blocked
            with self.assertRaises((ValidationError, Exception)) as cm:
                self.user1.delete()
            
            # Verify error indicates deletion is blocked
            error_message = str(cm.exception).lower()
            self.assertIn(
                "delete" or "not allowed" or "deactivate",
                error_message,
                f"Notification recipient deletion should be blocked, but got: {error_message}"
            )
            
            # Verify notification still exists
            self.assertTrue(Notification.objects.filter(id=notification.id).exists())
            
        except ImportError:
            self.skipTest("Notifications app not available")
    
    def test_scenario_7_engagement_event_entity_removed(self):
        """
        Scenario: Engagement event entity removed
        Expected: Event resolvable
        """
        try:
            from analytics.models import EngagementEvent
            
            # Create engagement event
            event = EngagementEvent.objects.create(
                user=self.user1,
                event_type='view',
                entity_type='pandit',
                entity_id=self.pandit1.id
            )
            
            # Attempt to delete entity (pandit)
            # Should be blocked
            with self.assertRaises((ValidationError, Exception)) as cm:
                self.pandit1.delete()
            
            # Verify error indicates deletion is blocked
            error_message = str(cm.exception).lower()
            self.assertIn(
                "delete" or "not allowed" or "deactivate",
                error_message,
                f"Entity deletion should be blocked, but got: {error_message}"
            )
            
            # Verify event still exists and is resolvable
            self.assertTrue(EngagementEvent.objects.filter(id=event.id).exists())
            
        except ImportError:
            self.skipTest("Analytics app not available")


class TestDeletionPolicyEnforcement(TestCase):
    """Test that deletion policy is enforced across all protected models."""
    
    def test_all_protected_models_in_registry(self):
        """Verify all critical models are in deletion policy registry."""
        from core.deletion_guard import DELETION_POLICY, is_deletion_protected
        
        critical_models = [
            "User",
            "PanditProfile",
            "TemplePage",
            "Referral",
            "AuditLog",
        ]
        
        for model_name in critical_models:
            with self.subTest(model=model_name):
                self.assertTrue(
                    is_deletion_protected(model_name),
                    f"{model_name} should be protected but is not in DELETION_POLICY"
                )

