import uuid
from django.db import models
from django.contrib.auth import get_user_model

"""
STRICT ISOLATION RULES:

- Do NOT import PanditProfile
- Do NOT join Pandit tables
- Do NOT reuse booking/review logic from other modules
- All bureau logic must remain self-contained

Violations will break architecture guarantees.
"""

User = get_user_model()


class BureauProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="bureau_profile",
    )

    # Basic
    bureau_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Contact
    phone_number = models.CharField(max_length=20)
    whatsapp_number = models.CharField(max_length=20, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=120)

    # Media
    profile_image = models.ImageField(upload_to="bureaus/profile/", blank=True, null=True)
    cover_image = models.ImageField(upload_to="bureaus/cover/", blank=True, null=True)

    # Caste storage (structured JSON)
    caste_data = models.JSONField(default=dict, blank=True)

    # Status flags
    is_active = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)

    # Public identifier for non-enumerable access to public pages
    public_id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Bureau Profile"
        verbose_name_plural = "Bureau Profiles"

    def __str__(self):
        return self.bureau_name


class BureauBookingIntent(models.Model):
    STATUS_PENDING = "pending"
    STATUS_VIEWED = "viewed"
    STATUS_RESPONDED = "responded"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_VIEWED, "Viewed"),
        (STATUS_RESPONDED, "Responded"),
    )

    bureau = models.ForeignKey(
        BureauProfile,
        on_delete=models.CASCADE,
        related_name="booking_intents",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    is_viewed = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} -> {self.bureau.bureau_name}"


class BureauReview(models.Model):
    bureau = models.ForeignKey(
        BureauProfile,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField()
    review_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Review {self.rating}/5 for {self.bureau.bureau_name}"
