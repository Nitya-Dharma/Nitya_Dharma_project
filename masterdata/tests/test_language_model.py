"""
Unit tests for Language master data model.

Tests:
- Model creation and validation
- Public ID generation
- Soft deletion (deactivate)
- Hard deletion prevention
- Admin restrictions
"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from masterdata.models import Language


class LanguageModelTest(TestCase):
    """Test Language model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.language_data = {
            'code': 'en',
            'name': 'English',
            'native_name': 'English',
            'is_active': True,
        }
    
    def test_language_creation(self):
        """Test creating a Language instance."""
        language = Language.objects.create(**self.language_data)
        
        self.assertIsNotNone(language.id)
        self.assertEqual(language.code, 'en')
        self.assertEqual(language.name, 'English')
        self.assertEqual(language.status, Language.STATUS_ACTIVE)
        self.assertTrue(language.is_active)
    
    def test_public_id_auto_generation(self):
        """Test that public_id is auto-generated on save."""
        language = Language.objects.create(**self.language_data)
        
        self.assertIsNotNone(language.public_id)
        self.assertGreater(len(language.public_id), 0)
    
    def test_language_str_with_native_name(self):
        """Test __str__ method with native name."""
        language = Language.objects.create(
            code='hi',
            name='Hindi',
            native_name='हिन्दी',
            is_active=True
        )
        
        self.assertIn('Hindi', str(language))
        self.assertIn('हिन्दी', str(language))
    
    def test_language_str_without_native_name(self):
        """Test __str__ method without native name."""
        language = Language.objects.create(
            code='te',
            name='Telugu',
            native_name=None,
            is_active=True
        )
        
        self.assertEqual(str(language), 'Telugu')
    
    def test_language_code_unique(self):
        """Test that language code must be unique."""
        Language.objects.create(**self.language_data)
        
        with self.assertRaises(Exception):  # IntegrityError or ValidationError
            Language.objects.create(
                code='en',  # Duplicate code
                name='English (Duplicate)',
                is_active=True
            )
    
    def test_language_deactivate(self):
        """Test deactivating a language."""
        language = Language.objects.create(**self.language_data)
        
        language.deactivate(reason="Test deactivation")
        
        language.refresh_from_db()
        self.assertEqual(language.status, Language.STATUS_INACTIVE)
        self.assertFalse(language.is_active)
    
    def test_language_hard_delete_prevention(self):
        """Test that hard deletion is prevented."""
        language = Language.objects.create(**self.language_data)
        
        with self.assertRaises(ValidationError) as context:
            language.delete()
        
        self.assertIn('Hard deletion is not allowed', str(context.exception))
        # Verify language still exists
        self.assertTrue(Language.objects.filter(id=language.id).exists())
    
    def test_language_default_status(self):
        """Test default status is ACTIVE."""
        language = Language.objects.create(**self.language_data)
        
        self.assertEqual(language.status, Language.STATUS_ACTIVE)
        self.assertTrue(language.is_active)
    
    def test_language_ordering(self):
        """Test that languages are ordered by name."""
        Language.objects.create(code='z', name='Zulu', is_active=True)
        Language.objects.create(code='a', name='Arabic', is_active=True)
        Language.objects.create(code='b', name='Bengali', is_active=True)
        
        languages = list(Language.objects.all())
        self.assertEqual(languages[0].name, 'Arabic')
        self.assertEqual(languages[1].name, 'Bengali')
        self.assertEqual(languages[2].name, 'Zulu')
    
    def test_language_indexes(self):
        """Test that indexes are created correctly."""
        from django.db import connection
        
        with connection.cursor() as cursor:
            # Check if indexes exist (MySQL specific)
            cursor.execute("""
                SELECT INDEX_NAME 
                FROM INFORMATION_SCHEMA.STATISTICS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'masterdata_language'
                AND INDEX_NAME != 'PRIMARY'
            """)
            indexes = [row[0] for row in cursor.fetchall()]
            
            # Should have at least code and status indexes
            self.assertIn('language_code_idx', indexes)
            self.assertIn('language_status_idx', indexes)


class LanguageAdminTest(TestCase):
    """Test Language admin interface restrictions."""
    
    def setUp(self):
        """Set up test data."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Create superuser
        self.superuser = User.objects.create_superuser(
            email='super@test.com',
            password='testpass123'
        )
        
        # Create regular user
        self.regular_user = User.objects.create_user(
            email='user@test.com',
            password='testpass123'
        )
        
        self.language = Language.objects.create(
            code='en',
            name='English',
            is_active=True
        )
    
    def test_superuser_can_manage_language(self):
        """Test that superuser can manage languages."""
        from django.test import Client
        client = Client()
        client.force_login(self.superuser)
        
        # Should be able to access admin
        response = client.get('/admin/masterdata/language/')
        self.assertEqual(response.status_code, 200)
    
    def test_regular_user_cannot_manage_language(self):
        """Test that regular user cannot manage languages."""
        from django.test import Client
        client = Client()
        client.force_login(self.regular_user)
        
        # Should be redirected or forbidden
        response = client.get('/admin/masterdata/language/')
        self.assertIn(response.status_code, [302, 403])





