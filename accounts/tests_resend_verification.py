"""
Tests for email verification resend functionality.

TASK 8: Comprehensive testing for resend verification feature.
"""
import time
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from django.contrib.messages import get_messages

from .models import EmailVerificationToken
from .services import (
    resend_verification_email,
    VerificationAlreadyCompleted,
    CooldownNotElapsed
)
from .utils import is_admin, is_pandit

User = get_user_model()


class ResendVerificationServiceTests(TestCase):
    """Test the service layer for resend verification."""
    
    def setUp(self):
        """Set up test data."""
        # Create a Pandit user (unverified)
        self.pandit = User.objects.create_user(
            email='pandit@test.com',
            password='testpass123',
            role='pandit',
            status='pending',
            email_verified=False,
            email_verified_at=None,
            is_active=False
        )
        
        # Create an Admin Pandit
        self.admin_pandit = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='admin',
            status='active',
            email_verified=True,
            is_active=True,
            is_staff=True
        )
        
        # Create a Super Admin
        self.super_admin = User.objects.create_superuser(
            email='superadmin@test.com',
            password='testpass123',
            role='admin',
            status='active'
        )
    
    def test_resend_for_unverified_pandit(self):
        """Test resending verification email for unverified Pandit."""
        token = resend_verification_email(self.pandit)
        
        self.assertIsNotNone(token)
        self.assertIsInstance(token, EmailVerificationToken)
        self.assertEqual(token.user, self.pandit)
        self.assertFalse(token.is_used)
        
        # Check that last_verification_email_sent_at was updated
        self.pandit.refresh_from_db()
        self.assertIsNotNone(self.pandit.last_verification_email_sent_at)
    
    def test_resend_blocked_for_verified_pandit(self):
        """Test that resend is blocked for already verified Pandit."""
        self.pandit.email_verified = True
        self.pandit.email_verified_at = timezone.now()
        self.pandit.save()
        
        with self.assertRaises(VerificationAlreadyCompleted):
            resend_verification_email(self.pandit)
    
    def test_resend_cooldown_enforcement(self):
        """Test that 30-second cooldown is enforced."""
        # First resend should succeed
        token1 = resend_verification_email(self.pandit)
        self.assertIsNotNone(token1)
        
        # Immediate second resend should fail
        with self.assertRaises(CooldownNotElapsed):
            resend_verification_email(self.pandit)
        
        # Wait 31 seconds (simulate time passing)
        # In real test, we'd mock time, but for simplicity, we'll update the timestamp
        self.pandit.last_verification_email_sent_at = timezone.now() - timedelta(seconds=31)
        self.pandit.save()
        
        # Now resend should succeed
        token2 = resend_verification_email(self.pandit)
        self.assertIsNotNone(token2)
    
    def test_resend_only_for_pandits(self):
        """Test that resend only works for Pandit role."""
        # Try to resend for admin user
        with self.assertRaises(Exception) as context:
            resend_verification_email(self.admin_pandit)
        
        self.assertIn("Pandit", str(context.exception))
    
    def test_resend_with_requested_by(self):
        """Test resend with requested_by parameter for audit logging."""
        token = resend_verification_email(
            user=self.pandit,
            requested_by=self.admin_pandit
        )
        
        self.assertIsNotNone(token)
        # Verify that last_verification_email_sent_at was updated
        self.pandit.refresh_from_db()
        self.assertIsNotNone(self.pandit.last_verification_email_sent_at)


class ResendVerificationViewTests(TestCase):
    """Test the view layer for resend verification."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create a Pandit user (unverified)
        self.pandit = User.objects.create_user(
            email='pandit@test.com',
            password='testpass123',
            role='pandit',
            status='pending',
            email_verified=False,
            email_verified_at=None,
            is_active=False
        )
        
        # Create another Pandit
        self.other_pandit = User.objects.create_user(
            email='otherpandit@test.com',
            password='testpass123',
            role='pandit',
            status='pending',
            email_verified=False,
            email_verified_at=None,
            is_active=False
        )
        
        # Create an Admin Pandit
        self.admin_pandit = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='admin',
            status='active',
            email_verified=True,
            is_active=True,
            is_staff=True
        )
        
        # Create a Super Admin
        self.super_admin = User.objects.create_superuser(
            email='superadmin@test.com',
            password='testpass123',
            role='admin',
            status='active'
        )
    
    def test_pandit_can_resend_for_self(self):
        """Test that Pandit can resend verification for themselves."""
        self.client.login(username='pandit@test.com', password='testpass123')
        
        url = reverse('accounts:resend_pandit_verification', args=[self.pandit.public_id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 302)  # Redirect
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('sent' in str(m).lower() for m in messages))
    
    def test_pandit_cannot_resend_for_others(self):
        """Test that Pandit cannot resend verification for other Pandits."""
        self.client.login(username='pandit@test.com', password='testpass123')
        
        url = reverse('accounts:resend_pandit_verification', args=[self.other_pandit.public_id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 302)  # Redirect
        
        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('permission' in str(m).lower() for m in messages))
    
    def test_admin_pandit_can_resend_for_any_pandit(self):
        """Test that Admin Pandit can resend verification for any Pandit."""
        self.client.login(username='admin@test.com', password='testpass123')
        
        url = reverse('accounts:resend_pandit_verification', args=[self.pandit.public_id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 302)  # Redirect
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('sent' in str(m).lower() for m in messages))
    
    def test_super_admin_can_resend_for_any_pandit(self):
        """Test that Super Admin can resend verification for any Pandit."""
        self.client.login(username='superadmin@test.com', password='testpass123')
        
        url = reverse('accounts:resend_pandit_verification', args=[self.pandit.public_id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 302)  # Redirect
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('sent' in str(m).lower() for m in messages))
    
    def test_resend_requires_login(self):
        """Test that resend requires authentication."""
        url = reverse('accounts:resend_pandit_verification', args=[self.pandit.public_id])
        response = self.client.post(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_resend_cooldown_message(self):
        """Test that cooldown message is shown when resend is too soon."""
        self.client.login(username='pandit@test.com', password='testpass123')
        
        url = reverse('accounts:resend_pandit_verification', args=[self.pandit.public_id])
        
        # First resend
        response1 = self.client.post(url)
        self.assertEqual(response1.status_code, 302)
        
        # Immediate second resend
        response2 = self.client.post(url)
        self.assertEqual(response2.status_code, 302)
        
        # Check warning message
        messages = list(get_messages(response2.wsgi_request))
        self.assertTrue(any('wait' in str(m).lower() or 'cooldown' in str(m).lower() for m in messages))
    
    def test_resend_for_already_verified_shows_info(self):
        """Test that resend for already verified Pandit shows info message."""
        self.pandit.email_verified = True
        self.pandit.email_verified_at = timezone.now()
        self.pandit.save()
        
        self.client.login(username='admin@test.com', password='testpass123')
        
        url = reverse('accounts:resend_pandit_verification', args=[self.pandit.public_id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 302)
        
        # Check info message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('already verified' in str(m).lower() or 'no action' in str(m).lower() for m in messages))


class ResendVerificationIntegrationTests(TestCase):
    """Integration tests for resend verification feature."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create a Pandit user (unverified)
        self.pandit = User.objects.create_user(
            email='pandit@test.com',
            password='testpass123',
            role='pandit',
            status='pending',
            email_verified=False,
            email_verified_at=None,
            is_active=False
        )
    
    def test_full_resend_flow(self):
        """Test the full flow: resend → verify email → cannot resend again."""
        # Step 1: Pandit resends verification
        self.client.login(username='pandit@test.com', password='testpass123')
        
        url = reverse('accounts:resend_pandit_verification', args=[self.pandit.public_id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        # Step 2: Get the verification token
        token = EmailVerificationToken.objects.filter(
            user=self.pandit,
            is_used=False
        ).order_by('-created_at').first()
        
        self.assertIsNotNone(token)
        
        # Step 3: Verify email
        verify_url = reverse('accounts:verify_email', args=[token.token])
        response = self.client.get(verify_url)
        self.assertEqual(response.status_code, 200)
        
        # Step 4: Check that user is now verified
        self.pandit.refresh_from_db()
        self.assertTrue(self.pandit.email_verified)
        self.assertIsNotNone(self.pandit.email_verified_at)
        
        # Step 5: Try to resend again (should fail)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('already verified' in str(m).lower() or 'no action' in str(m).lower() for m in messages))
