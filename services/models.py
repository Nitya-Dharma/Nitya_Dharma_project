from django.conf import settings
from django.db import models


class ExpertSocialLink(models.Model):
    expert = models.ForeignKey(
        "core.ExpertProfile",
        on_delete=models.CASCADE,
        related_name="social_links",
    )
    url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["expert", "url"],
                name="unique_expert_social_link",
            )
        ]

    def __str__(self):
        ident = self.expert.email or self.expert.name
        return f"{ident} - {self.url}"


class ExpertBookingIntent(models.Model):
    """
    Logged-in user booking intents for service experts (astrology / numerology / palmistry).
    Isolated from core.ExpertBookingIntent (legacy) via related_name service_booking_intents.
    """

    expert = models.ForeignKey(
        "core.ExpertProfile",
        on_delete=models.CASCADE,
        related_name="service_booking_intents",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    message = models.TextField()
    is_viewed = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.name} → {self.expert_id}"
