from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Availability(models.Model):
    """
    Availability model for Pandits.
    
    Represents Pandit-declared time windows when they are available.
    This is a signal, not a commitment or booking.
    
    Ownership:
    - One Pandit → Many Availability entries
    - Availability belongs exclusively to Pandit
    - Availability does NOT belong to users, leads, or bookings
    
    This model is:
    - Booking-agnostic
    - Payment-agnostic
    - KPI-agnostic
    - Search-friendly
    - Safe for future extensions
    
    NOTE: 
    - Role enforcement (role="pandit") is handled at service/permission layer, not DB level
    - No audit model or audit storage is implemented here; audit is deferred to Task 6.12
    - clean() method is for Django admin/forms only, not runtime enforcement
    """
    
    # DAY_OF_WEEK_CHOICES
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6
    
    DAY_OF_WEEK_CHOICES = [
        (MONDAY, 'Monday'),
        (TUESDAY, 'Tuesday'),
        (WEDNESDAY, 'Wednesday'),
        (THURSDAY, 'Thursday'),
        (FRIDAY, 'Friday'),
        (SATURDAY, 'Saturday'),
        (SUNDAY, 'Sunday'),
    ]
    
    # Ownership
    pandit = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='availabilities',
        verbose_name='Pandit',
        help_text='The Pandit who owns this availability entry. NOTE: Role enforcement (role="pandit") is handled at service/permission layer, not at database level. This ForeignKey does not enforce role constraints.'
    )
    
    # Temporal Fields
    day_of_week = models.IntegerField(
        choices=DAY_OF_WEEK_CHOICES,
        null=True,
        blank=True,
        verbose_name='Day of Week',
        help_text='Day of the week for recurring availability (0=Monday, 6=Sunday). Leave blank if using specific_date.'
    )
    specific_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Specific Date',
        help_text='Specific calendar date for one-off availability. Leave blank if using day_of_week for recurring pattern.'
    )
    start_time = models.TimeField(
        verbose_name='Start Time',
        help_text='Start time of availability window (e.g., 09:00)'
    )
    end_time = models.TimeField(
        verbose_name='End Time',
        help_text='End time of availability window (e.g., 17:00)'
    )
    is_recurring = models.BooleanField(
        default=True,
        verbose_name='Is Recurring',
        help_text='Descriptive field: True if using day_of_week (recurring), False if using specific_date (one-off). This is descriptive only and may be derived in future refactoring.'
    )
    
    # Contextual Fields (from Module 2 - Master Data)
    city = models.ForeignKey(
        'masterdata.City',
        on_delete=models.PROTECT,
        related_name='availabilities',
        verbose_name='City',
        help_text='City where this availability applies (mandatory)'
    )
    area = models.ForeignKey(
        'masterdata.LocalArea',
        on_delete=models.PROTECT,
        related_name='availabilities',
        null=True,
        blank=True,
        verbose_name='Local Area',
        help_text='Local area where this availability applies (optional)'
    )
    pooja = models.ForeignKey(
        'masterdata.Pooja',
        on_delete=models.PROTECT,
        related_name='availabilities',
        null=True,
        blank=True,
        verbose_name='Pooja',
        help_text='Pooja type for which this availability applies (optional)'
    )
    
    # State Fields (DESCRIPTIVE ONLY)
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active',
        help_text='Whether this availability entry is currently active. Descriptive only, does not enforce availability.'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At',
        help_text='When this availability entry was created'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At',
        help_text='When this availability entry was last updated'
    )
    
    class Meta:
        verbose_name = 'Availability'
        verbose_name_plural = 'Availabilities'
        db_table = 'availability_availability'
        ordering = ['pandit', 'day_of_week', 'specific_date', 'start_time']
        indexes = [
            models.Index(fields=['pandit', 'is_active']),
            models.Index(fields=['city', 'is_active']),
            models.Index(fields=['day_of_week', 'is_active']),
            models.Index(fields=['specific_date', 'is_active']),
        ]
    
    def __str__(self):
        """String representation of availability entry."""
        pandit_name = self.pandit.get_full_name() or self.pandit.email
        location = self.city.name
        if self.area:
            location = f"{self.area.name}, {location}"
        
        if self.is_recurring and self.day_of_week is not None:
            day_name = dict(self.DAY_OF_WEEK_CHOICES)[self.day_of_week]
            return f"{pandit_name} - {day_name} {self.start_time}-{self.end_time} ({location})"
        elif self.specific_date:
            return f"{pandit_name} - {self.specific_date} {self.start_time}-{self.end_time} ({location})"
        else:
            return f"{pandit_name} - {self.start_time}-{self.end_time} ({location})"
    
    def clean(self):
        """
        Validation logic for Django admin and forms.
        
        NOTE: This is NOT enforcement logic. Actual validation enforcement
        happens at the service/permission layer (Task 6.3 and beyond).
        This method is provided for Django admin and form validation only.
        
        Ensures either day_of_week OR specific_date is set, not both.
        """
        from django.core.exceptions import ValidationError
        
        # Either day_of_week or specific_date must be set, but not both
        if self.day_of_week is not None and self.specific_date is not None:
            raise ValidationError({
                'day_of_week': 'Cannot set both day_of_week and specific_date. Use day_of_week for recurring, specific_date for one-off.',
                'specific_date': 'Cannot set both day_of_week and specific_date. Use day_of_week for recurring, specific_date for one-off.'
            })
        
        if self.day_of_week is None and self.specific_date is None:
            raise ValidationError({
                'day_of_week': 'Either day_of_week (for recurring) or specific_date (for one-off) must be set.',
                'specific_date': 'Either day_of_week (for recurring) or specific_date (for one-off) must be set.'
            })
        
        # Validate time range
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError({
                'end_time': 'End time must be after start time.'
            })
    
    # NOTE: No save() override. Validation enforcement happens at service layer (Task 6.3+).
    # clean() is provided for Django admin/forms only, not for runtime enforcement.

