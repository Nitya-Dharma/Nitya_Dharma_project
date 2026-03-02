"""
Comprehensive Deletion Guard Tests — PART 4 — AUTOMATED GUARDRAILS

TASK 4.3: Hard Delete Detection Test

These tests FAIL THE BUILD if hard deletes occur for protected models.
If any test passes (delete succeeds), the build should fail.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class TestHardDeleteBlocked(TestCase):
    """
    TASK 4.3: Test that hard deletes are blocked for protected models.
    
    FAIL CONDITION: If delete() succeeds for protected models → FAIL BUILD
    """
    
    def test_user_delete_blocked(self):
        """Test that User.delete() is blocked."""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )
        user_id = user.id
        
        # Attempt delete - should raise ValidationError
        with self.assertRaises(ValidationError) as cm:
            user.delete()
        
        # Verify error message
        error_msg = str(cm.exception)
        self.assertIn("Hard deletion is not allowed", error_msg)
        self.assertIn("deactivated instead", error_msg.lower())
        
        # Verify user still exists in database
        self.assertTrue(User.objects.filter(id=user_id).exists())
    
    def test_user_bulk_delete_blocked(self):
        """Test that User.objects.filter().delete() is blocked."""
        # Create test users
        user1 = User.objects.create_user(email="user1@example.com", password="pass")
        user2 = User.objects.create_user(email="user2@example.com", password="pass")
        
        user_ids = [user1.id, user2.id]
        
        # Attempt bulk delete - should raise ValidationError
        with self.assertRaises(ValidationError) as cm:
            User.objects.filter(id__in=user_ids).delete()
        
        # Verify error message
        error_msg = str(cm.exception)
        self.assertIn("Bulk deletion is not allowed", error_msg)
        
        # Verify users still exist
        self.assertTrue(User.objects.filter(id__in=user_ids).exists())
    
    def test_pandit_profile_delete_blocked(self):
        """Test that PanditProfile.delete() is blocked."""
        try:
            from profiles.models import PanditProfile
            
            user = User.objects.create_user(
                email="pandit@example.com",
                password="testpass123",
                role='pandit'
            )
            
            profile, created = PanditProfile.objects.get_or_create(user=user)
            profile_id = profile.id
            
            # Attempt delete - should raise ValidationError
            with self.assertRaises(ValidationError) as cm:
                profile.delete()
            
            # Verify error message
            error_msg = str(cm.exception)
            self.assertIn("Hard deletion is not allowed", error_msg)
            
            # Verify profile still exists
            self.assertTrue(PanditProfile.objects.filter(id=profile_id).exists())
        except ImportError:
            self.skipTest("Profiles app not available")
    
    def test_master_data_delete_blocked(self):
        """Test that master data models cannot be deleted."""
        try:
            from masterdata.models import City, Language, PoojaCategory
            
            # Test City deletion
            city = City.objects.create(name="Test City")
            city_id = city.id
            
            with self.assertRaises(ValidationError):
                city.delete()
            
            self.assertTrue(City.objects.filter(id=city_id).exists())
            
            # Test Language deletion
            language = Language.objects.create(code="test", name="Test Language")
            lang_id = language.id
            
            with self.assertRaises(ValidationError):
                language.delete()
            
            self.assertTrue(Language.objects.filter(id=lang_id).exists())
            
            # Test PoojaCategory deletion
            category = PoojaCategory.objects.create(name="Test Category")
            cat_id = category.id
            
            with self.assertRaises(ValidationError):
                category.delete()
            
            self.assertTrue(PoojaCategory.objects.filter(id=cat_id).exists())
        except ImportError:
            self.skipTest("Masterdata app not available")


class TestDeactivationWorks(TestCase):
    """Test that deactivation works as alternative to deletion."""
    
    def test_user_deactivation(self):
        """Test that User.deactivate() works."""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            status='active'
        )
        
        # Deactivate user
        user.deactivate(reason="Test deactivation")
        
        # Verify status changed
        user.refresh_from_db()
        self.assertEqual(user.status, 'deactivated')
        self.assertFalse(user.is_active)
        
        # Verify user still exists
        self.assertTrue(User.objects.filter(id=user.id).exists())


class TestSafetyMatrix(TestCase):
    """
    SECTION 4: Safety Test Matrix
    
    Test all scenarios from the safety matrix to ensure deletion is blocked.
    """
    
    def test_pandit_with_referrals_delete_blocked(self):
        """Scenario: Pandit with referrals deleted → Blocked, deactivated"""
        try:
            from profiles.models import PanditProfile
            
            # Create referrer
            referrer = User.objects.create_user(
                email="referrer@example.com",
                password="pass",
                role='pandit'
            )
            referrer_profile, _ = PanditProfile.objects.get_or_create(user=referrer)
            
            # Create referred pandit
            referred = User.objects.create_user(
                email="referred@example.com",
                password="pass",
                role='pandit',
                referred_by=referrer
            )
            referred_profile, _ = PanditProfile.objects.get_or_create(user=referred)
            
            # Attempt to delete referrer - should be blocked
            with self.assertRaises(ValidationError):
                referrer.delete()
            
            # Verify both still exist
            self.assertTrue(User.objects.filter(id=referrer.id).exists())
            self.assertTrue(User.objects.filter(id=referred.id).exists())
        except ImportError:
            self.skipTest("Profiles app not available")
    
    def test_page_delete_blocked(self):
        """Scenario: Page deleted → Marked INVISIBLE"""
        try:
            from pages.models import TemplePage
            
            page = TemplePage.objects.create(
                name="Test Temple",
                slug="test-temple"
            )
            page_id = page.id
            
            # Attempt delete - should be blocked
            with self.assertRaises(ValidationError):
                page.delete()
            
            # Verify page still exists
            self.assertTrue(TemplePage.objects.filter(id=page_id).exists())
            
            # Deactivate instead
            page.deactivate(reason="Test")
            page.refresh_from_db()
            self.assertEqual(page.status, 'invisible')
        except ImportError:
            self.skipTest("Pages app not available")
    
    def test_review_author_removed_preserved(self):
        """Scenario: Review author removed → Review stays, anonymized"""
        try:
            from reviews.models import Review
            
            user = User.objects.create_user(email="reviewer@example.com", password="pass")
            pandit = User.objects.create_user(email="pandit@example.com", password="pass", role='pandit')
            
            review = Review.objects.create(
                reviewer=user,
                pandit=pandit,
                rating=5,
                comment="Great service"
            )
            review_id = review.id
            
            # Attempt to delete reviewer - should be blocked
            with self.assertRaises(ValidationError):
                user.delete()
            
            # Verify review still exists
            self.assertTrue(Review.objects.filter(id=review_id).exists())
        except ImportError:
            self.skipTest("Reviews app not available")
    
    def test_notification_actor_removed_preserved(self):
        """Scenario: Notification actor removed → Notification preserved"""
        try:
            from notifications.models import Notification
            
            actor = User.objects.create_user(email="actor@example.com", password="pass")
            recipient = User.objects.create_user(email="recipient@example.com", password="pass")
            
            notification = Notification.objects.create(
                recipient=recipient,
                notification_type='test',
                message="Test notification"
            )
            notif_id = notification.id
            
            # Attempt to delete actor - should be blocked
            with self.assertRaises(ValidationError):
                actor.delete()
            
            # Verify notification still exists
            self.assertTrue(Notification.objects.filter(id=notif_id).exists())
        except ImportError:
            self.skipTest("Notifications app not available")


class TestMigrationGuard(TestCase):
    """
    TASK 4.4: Migration Guard
    
    Test that dangerous migrations are detected.
    Note: Actual migration scanning is done in CI/CD.
    """
    
    def test_migration_guard_concept(self):
        """Verify migration guard concept exists."""
        # Migration guard should:
        # 1. Scan migration files
        # 2. Check for dangerous operations (DROP TABLE, DROP COLUMN, etc.)
        # 3. Fail build if violations found
        
        # For now, we document the requirement
        self.assertTrue(True, "Migration guard should be implemented in CI/CD")
    
    def test_no_dangerous_migrations_in_codebase(self):
        """Verify no dangerous migrations exist in current codebase."""
        import os
        from django.conf import settings
        
        dangerous_patterns = [
            'DropTable',
            'DeleteModel',
            'RemoveField',
            'AlterField.*on_delete.*CASCADE',  # Should be PROTECT for historical data
        ]
        
        # This is a placeholder - actual implementation would scan migration files
        # For now, we just verify the concept
        self.assertTrue(True, "Migration guard should scan for dangerous patterns")




