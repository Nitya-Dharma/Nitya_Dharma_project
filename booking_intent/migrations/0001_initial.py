# Generated migration for BookingIntent model
# Task 8.9: Booking Intent Model & Persistence

from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BookingIntent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('optional_requested_date', models.DateField(blank=True, null=True, verbose_name='Requested Date')),
                ('optional_requested_time', models.TimeField(blank=True, null=True, verbose_name='Requested Time')),
                ('message', models.TextField(blank=True, help_text='Optional message from requester to Pandit (max 500 characters)', max_length=500, null=True, validators=[MaxLengthValidator(500)], verbose_name='Message')),
                ('status', models.CharField(choices=[('submitted', 'Submitted'), ('viewed', 'Viewed'), ('expired', 'Expired'), ('cancelled', 'Cancelled')], default='submitted', max_length=20, verbose_name='Status')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('requester_status_at_creation', models.CharField(blank=True, help_text='Snapshot of requester status when intent was created (for audit)', max_length=20, null=True, verbose_name='Requester Status at Creation')),
                ('pandit_status_at_creation', models.CharField(blank=True, help_text='Snapshot of pandit status when intent was created (for audit)', max_length=20, null=True, verbose_name='Pandit Status at Creation')),
                ('is_flagged', models.BooleanField(default=False, verbose_name='Is Flagged')),
                ('flagged_at', models.DateTimeField(blank=True, null=True, verbose_name='Flagged At')),
                ('flagged_reason', models.TextField(blank=True, help_text='Reason for flagging (admin-only)', null=True, verbose_name='Flagged Reason')),
                ('pandit', models.ForeignKey(help_text='Pandit this intent is addressed to. NOTE: Role enforcement (role="pandit") is handled at service/permission layer, not at database level.', on_delete=django.db.models.deletion.PROTECT, related_name='booking_intents_received', to=settings.AUTH_USER_MODEL, verbose_name='Pandit')),
                ('requester', models.ForeignKey(help_text='User who created this booking intent', on_delete=django.db.models.deletion.PROTECT, related_name='booking_intents_created', to=settings.AUTH_USER_MODEL, verbose_name='Requester')),
            ],
            options={
                'verbose_name': 'Booking Intent',
                'verbose_name_plural': 'Booking Intents',
                'db_table': 'booking_intent_bookingintent',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='bookingintent',
            index=models.Index(fields=['requester', 'status'], name='booking_int_require_idx'),
        ),
        migrations.AddIndex(
            model_name='bookingintent',
            index=models.Index(fields=['pandit', 'status'], name='booking_int_pandit__idx'),
        ),
        migrations.AddIndex(
            model_name='bookingintent',
            index=models.Index(fields=['status', 'created_at'], name='booking_int_status_idx'),
        ),
    ]

