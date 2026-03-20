from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ('profiles', '0007_add_custom_location_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='PendingLocation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Display name submitted by user (state/city/area depending on type).', max_length=100, verbose_name='Name')),
                ('normalized_name', models.CharField(db_index=True, help_text='Lowercased normalization used for duplicate prevention.', max_length=220, verbose_name='Normalized Name')),
                ('type', models.CharField(choices=[('state', 'State'), ('city', 'City'), ('area', 'Area')], db_index=True, max_length=10, verbose_name='Type')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], db_index=True, default='pending', max_length=20, verbose_name='Status')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('reviewed_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pending_locations_created', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('related_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pending_locations', to='profiles.PanditProfile', verbose_name='Related Profile')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pending_locations_reviewed', to=settings.AUTH_USER_MODEL, verbose_name='Reviewed By')),
            ],
            options={
                'verbose_name': 'Pending Location',
                'verbose_name_plural': 'Pending Locations',
                'db_table': 'profiles_pending_location',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='pendinglocation',
            index=models.Index(fields=['type', 'normalized_name'], name='pendingloc_type_norm_idx'),
        ),
        migrations.AddIndex(
            model_name='pendinglocation',
            index=models.Index(fields=['status', 'type', 'created_at'], name='pl_status_type_created_idx'),
        ),
    ]

