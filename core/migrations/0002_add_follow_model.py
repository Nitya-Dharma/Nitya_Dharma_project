# Generated manually for Follow model
# Migration: 0002_add_follow_model

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import core.public_id


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Follow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public_id', models.CharField(blank=True, db_index=True, editable=False, help_text='Public-facing UUIDv7 identifier', max_length=36, null=True, unique=True, verbose_name='Public ID')),
                ('entity_type', models.CharField(choices=[('pandit', 'Pandit'), ('temple', 'Temple')], db_index=True, help_text='Type of entity being followed (pandit or temple)', max_length=20, verbose_name='Entity Type')),
                ('entity_id', models.BigIntegerField(db_index=True, help_text='ID of the entity being followed (PanditProfile.id or Page.id)', verbose_name='Entity ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Timestamp when user started following the entity', verbose_name='Created At')),
                ('user', models.ForeignKey(help_text='End User following the entity', on_delete=django.db.models.deletion.CASCADE, related_name='follows', to=settings.AUTH_USER_MODEL, verbose_name='Follower')),
            ],
            options={
                'verbose_name': 'Follow',
                'verbose_name_plural': 'Follows',
                'db_table': 'core_follow',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='follow',
            index=models.Index(fields=['user', 'entity_type', 'entity_id'], name='core_follow_user_entity_idx'),
        ),
        migrations.AddIndex(
            model_name='follow',
            index=models.Index(fields=['entity_type', 'entity_id', 'created_at'], name='core_follow_entity_created_idx'),
        ),
        migrations.AddIndex(
            model_name='follow',
            index=models.Index(fields=['entity_type', 'entity_id'], name='core_follow_entity_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='follow',
            unique_together={('user', 'entity_type', 'entity_id')},
        ),
    ]















