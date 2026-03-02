"""
Unit tests for PART 2 master tables:
- PoojaCategory (enhanced)
- CountryCode
- ProfileCompletionRule
- UploadConfig

Tests:
- Model creation and validation
- Public ID generation
- Soft deletion (deactivate)
- Hard deletion prevention
- Admin restrictions
- Immutability rules
"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from masterdata.models import (
    PoojaCategory, CountryCode, ProfileCompletionRule, UploadConfig
)


class PoojaCategoryEnhancedTest(TestCase):
    """Test enhanced PoojaCategory model."""
    
    def setUp(self):
        """Set up test data."""
        self.category_data = {
            'name': 'Daily & Common Household Poojas',
            'description': 'Regular household poojas',
            'display_order': 1,
            'is_active': True,
        }
    
    def test_category_creation(self):
        """Test creating a PoojaCategory instance."""
        category = PoojaCategory.objects.create(**self.category_data)
        
        self.assertIsNotNone(category.id)
        self.assertEqual(category.name, 'Daily & Common Household Poojas')
        self.assertEqual(category.display_order, 1)
        self.assertTrue(category.is_active)
    
    def test_category_ordering(self):
        """Test that categories are ordered by display_order then name."""
        PoojaCategory.objects.create(name='Z Category', display_order=3, is_active=True)
        PoojaCategory.objects.create(name='A Category', display_order=1, is_active=True)
        PoojaCategory.objects.create(name='B Category', display_order=2, is_active=True)
        
        categories = list(PoojaCategory.objects.all())
        self.assertEqual(categories[0].name, 'A Category')
        self.assertEqual(categories[1].name, 'B Category')
        self.assertEqual(categories[2].name, 'Z Category')
    
    def test_category_deactivate(self):
        """Test deactivating a category."""
        category = PoojaCategory.objects.create(**self.category_data)
        
        category.deactivate(reason="Test deactivation")
        
        category.refresh_from_db()
        self.assertEqual(category.status, PoojaCategory.STATUS_INACTIVE)
        self.assertFalse(category.is_active)
    
    def test_category_hard_delete_prevention(self):
        """Test that hard deletion is prevented."""
        category = PoojaCategory.objects.create(**self.category_data)
        
        with self.assertRaises(ValidationError) as context:
            category.delete()
        
        self.assertIn('Hard deletion is not allowed', str(context.exception))
        self.assertTrue(PoojaCategory.objects.filter(id=category.id).exists())


class CountryCodeTest(TestCase):
    """Test CountryCode model."""
    
    def setUp(self):
        """Set up test data."""
        self.country_data = {
            'country_name': 'India',
            'iso_code': 'IN',
            'dial_code': '+91',
            'is_active': True,
        }
    
    def test_country_code_creation(self):
        """Test creating a CountryCode instance."""
        country = CountryCode.objects.create(**self.country_data)
        
        self.assertIsNotNone(country.id)
        self.assertEqual(country.country_name, 'India')
        self.assertEqual(country.iso_code, 'IN')
        self.assertEqual(country.dial_code, '+91')
        self.assertTrue(country.is_active)
    
    def test_country_code_str(self):
        """Test __str__ method."""
        country = CountryCode.objects.create(**self.country_data)
        
        self.assertIn('India', str(country))
        self.assertIn('+91', str(country))
    
    def test_country_code_iso_unique(self):
        """Test that ISO code must be unique."""
        CountryCode.objects.create(**self.country_data)
        
        with self.assertRaises(Exception):  # IntegrityError
            CountryCode.objects.create(
                country_name='India (Duplicate)',
                iso_code='IN',  # Duplicate
                dial_code='+91',
                is_active=True
            )
    
    def test_country_code_deactivate(self):
        """Test deactivating a country code."""
        country = CountryCode.objects.create(**self.country_data)
        
        country.deactivate(reason="Test deactivation")
        
        country.refresh_from_db()
        self.assertEqual(country.status, CountryCode.STATUS_INACTIVE)
        self.assertFalse(country.is_active)
    
    def test_country_code_hard_delete_prevention(self):
        """Test that hard deletion is prevented."""
        country = CountryCode.objects.create(**self.country_data)
        
        with self.assertRaises(ValidationError) as context:
            country.delete()
        
        self.assertIn('Hard deletion is not allowed', str(context.exception))
        self.assertTrue(CountryCode.objects.filter(id=country.id).exists())


class ProfileCompletionRuleTest(TestCase):
    """Test ProfileCompletionRule model."""
    
    def setUp(self):
        """Set up test data."""
        self.rule_data = {
            'field_name': 'full_name',
            'display_label': 'Full Name',
            'is_required': True,
            'weight': 20,
            'is_active': True,
        }
    
    def test_rule_creation(self):
        """Test creating a ProfileCompletionRule instance."""
        rule = ProfileCompletionRule.objects.create(**self.rule_data)
        
        self.assertIsNotNone(rule.id)
        self.assertEqual(rule.field_name, 'full_name')
        self.assertEqual(rule.display_label, 'Full Name')
        self.assertEqual(rule.weight, 20)
        self.assertTrue(rule.is_required)
    
    def test_rule_str(self):
        """Test __str__ method."""
        rule = ProfileCompletionRule.objects.create(**self.rule_data)
        
        self.assertIn('Full Name', str(rule))
        self.assertIn('full_name', str(rule))
    
    def test_rule_field_name_unique(self):
        """Test that field_name must be unique."""
        ProfileCompletionRule.objects.create(**self.rule_data)
        
        with self.assertRaises(Exception):  # IntegrityError
            ProfileCompletionRule.objects.create(
                field_name='full_name',  # Duplicate
                display_label='Full Name (Duplicate)',
                is_required=True,
                weight=10,
                is_active=True
            )
    
    def test_rule_ordering(self):
        """Test that rules are ordered by weight then field_name."""
        ProfileCompletionRule.objects.create(
            field_name='z_field', display_label='Z Field', weight=30, is_active=True
        )
        ProfileCompletionRule.objects.create(
            field_name='a_field', display_label='A Field', weight=10, is_active=True
        )
        ProfileCompletionRule.objects.create(
            field_name='b_field', display_label='B Field', weight=20, is_active=True
        )
        
        rules = list(ProfileCompletionRule.objects.all())
        self.assertEqual(rules[0].field_name, 'a_field')
        self.assertEqual(rules[1].field_name, 'b_field')
        self.assertEqual(rules[2].field_name, 'z_field')
    
    def test_rule_deactivate(self):
        """Test deactivating a rule."""
        rule = ProfileCompletionRule.objects.create(**self.rule_data)
        
        rule.deactivate(reason="Test deactivation")
        
        rule.refresh_from_db()
        self.assertEqual(rule.status, ProfileCompletionRule.STATUS_INACTIVE)
        self.assertFalse(rule.is_active)
    
    def test_rule_hard_delete_prevention(self):
        """Test that hard deletion is prevented."""
        rule = ProfileCompletionRule.objects.create(**self.rule_data)
        
        with self.assertRaises(ValidationError) as context:
            rule.delete()
        
        self.assertIn('Hard deletion is not allowed', str(context.exception))
        self.assertTrue(ProfileCompletionRule.objects.filter(id=rule.id).exists())


class UploadConfigTest(TestCase):
    """Test UploadConfig model."""
    
    def setUp(self):
        """Set up test data."""
        self.config_data = {
            'key': 'profile_image',
            'max_size_mb': 5,
            'allowed_mime_types': ['image/jpeg', 'image/png', 'image/webp'],
            'recommended_dimensions': '500x500px',
            'is_active': True,
        }
    
    def test_config_creation(self):
        """Test creating an UploadConfig instance."""
        config = UploadConfig.objects.create(**self.config_data)
        
        self.assertIsNotNone(config.id)
        self.assertEqual(config.key, 'profile_image')
        self.assertEqual(config.max_size_mb, 5)
        self.assertEqual(len(config.allowed_mime_types), 3)
        self.assertEqual(config.recommended_dimensions, '500x500px')
    
    def test_config_str(self):
        """Test __str__ method."""
        config = UploadConfig.objects.create(**self.config_data)
        
        self.assertIn('profile_image', str(config))
        self.assertIn('5MB', str(config))
    
    def test_config_key_unique(self):
        """Test that key must be unique."""
        UploadConfig.objects.create(**self.config_data)
        
        with self.assertRaises(Exception):  # IntegrityError
            UploadConfig.objects.create(
                key='profile_image',  # Duplicate
                max_size_mb=10,
                allowed_mime_types=['image/jpeg'],
                is_active=True
            )
    
    def test_config_json_field(self):
        """Test that allowed_mime_types is stored as JSON."""
        config = UploadConfig.objects.create(**self.config_data)
        
        config.refresh_from_db()
        self.assertIsInstance(config.allowed_mime_types, list)
        self.assertIn('image/jpeg', config.allowed_mime_types)
        self.assertIn('image/png', config.allowed_mime_types)
    
    def test_config_deactivate(self):
        """Test deactivating a config."""
        config = UploadConfig.objects.create(**self.config_data)
        
        config.deactivate(reason="Test deactivation")
        
        config.refresh_from_db()
        self.assertEqual(config.status, UploadConfig.STATUS_INACTIVE)
        self.assertFalse(config.is_active)
    
    def test_config_hard_delete_prevention(self):
        """Test that hard deletion is prevented."""
        config = UploadConfig.objects.create(**self.config_data)
        
        with self.assertRaises(ValidationError) as context:
            config.delete()
        
        self.assertIn('Hard deletion is not allowed', str(context.exception))
        self.assertTrue(UploadConfig.objects.filter(id=config.id).exists())


class MasterTablesImmutabilityTest(TestCase):
    """Test immutability rules across all master tables."""
    
    def test_all_models_prevent_hard_delete(self):
        """Test that all master tables prevent hard deletion."""
        category = PoojaCategory.objects.create(
            name='Test Category', is_active=True
        )
        country = CountryCode.objects.create(
            country_name='Test Country', iso_code='TC', dial_code='+99', is_active=True
        )
        rule = ProfileCompletionRule.objects.create(
            field_name='test_field', display_label='Test Field', is_active=True
        )
        config = UploadConfig.objects.create(
            key='test_config', max_size_mb=5, allowed_mime_types=[], is_active=True
        )
        
        # All should raise ValidationError on delete
        with self.assertRaises(ValidationError):
            category.delete()
        with self.assertRaises(ValidationError):
            country.delete()
        with self.assertRaises(ValidationError):
            rule.delete()
        with self.assertRaises(ValidationError):
            config.delete()
        
        # All should still exist
        self.assertTrue(PoojaCategory.objects.filter(id=category.id).exists())
        self.assertTrue(CountryCode.objects.filter(id=country.id).exists())
        self.assertTrue(ProfileCompletionRule.objects.filter(id=rule.id).exists())
        self.assertTrue(UploadConfig.objects.filter(id=config.id).exists())
    
    def test_all_models_support_deactivate(self):
        """Test that all master tables support deactivate."""
        category = PoojaCategory.objects.create(
            name='Test Category', is_active=True
        )
        country = CountryCode.objects.create(
            country_name='Test Country', iso_code='TC', dial_code='+99', is_active=True
        )
        rule = ProfileCompletionRule.objects.create(
            field_name='test_field', display_label='Test Field', is_active=True
        )
        config = UploadConfig.objects.create(
            key='test_config', max_size_mb=5, allowed_mime_types=[], is_active=True
        )
        
        # All should support deactivate
        category.deactivate()
        country.deactivate()
        rule.deactivate()
        config.deactivate()
        
        # All should be inactive
        category.refresh_from_db()
        country.refresh_from_db()
        rule.refresh_from_db()
        config.refresh_from_db()
        
        self.assertFalse(category.is_active)
        self.assertFalse(country.is_active)
        self.assertFalse(rule.is_active)
        self.assertFalse(config.is_active)





