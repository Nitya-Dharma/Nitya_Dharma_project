from django.core.mail import send_mail
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import BureauProfile


def _is_bureau_email_eligible(profile):
    return bool(profile.is_approved and profile.is_active and profile.is_email_verified)


def trigger_email(profile):
    user_email = getattr(profile.user, "email", "") or ""
    if not user_email:
        return

    subject = "Your Bureau Account is Approved"
    message = f"""
Hello {profile.bureau_name},

Your Hindu Marriage Bureau account has been approved.

You can now log in and access your dashboard.

Regards,
Nitya Dharma Team
"""
    send_mail(
        subject,
        message,
        None,
        [user_email],
        fail_silently=True,
    )


@receiver(pre_save, sender=BureauProfile)
def store_previous_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_is_eligible = False
        return

    try:
        old = sender.objects.only("is_approved", "is_active", "is_email_verified").get(pk=instance.pk)
        instance._previous_is_eligible = _is_bureau_email_eligible(old)
    except Exception:
        instance._previous_is_eligible = False


@receiver(post_save, sender=BureauProfile)
def send_email_on_approval(sender, instance, created, **kwargs):
    if created:
        return

    current_is_eligible = _is_bureau_email_eligible(instance)

    if not getattr(instance, "_previous_is_eligible", False) and current_is_eligible:
        trigger_email(instance)
