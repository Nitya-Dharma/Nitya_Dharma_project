# Phase 10F: Related searches analytics
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('search', '0002_searchquerylog'),
    ]

    operations = [
        migrations.CreateModel(
            name='RelatedSearchLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_query', models.CharField(db_index=True, max_length=100)),
                ('related_query', models.CharField(db_index=True, max_length=100)),
                ('pair_count', models.PositiveIntegerField(default=1)),
                ('last_seen', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'search_relatedsearchlog',
                'verbose_name': 'Related Search Log',
                'verbose_name_plural': 'Related Search Logs',
                'ordering': ['-pair_count'],
            },
        ),
        migrations.AddIndex(
            model_name='relatedsearchlog',
            index=models.Index(fields=['source_query'], name='search_rsl_source_idx'),
        ),
        migrations.AddIndex(
            model_name='relatedsearchlog',
            index=models.Index(fields=['related_query'], name='search_rsl_related_idx'),
        ),
        migrations.AddIndex(
            model_name='relatedsearchlog',
            index=models.Index(fields=['-pair_count'], name='search_rsl_count_idx'),
        ),
    ]
