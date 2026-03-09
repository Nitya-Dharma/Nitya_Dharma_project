# Phase 10E: Search analytics model for trending searches
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('search', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SearchQueryLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query', models.CharField(db_index=True, max_length=100)),
                ('normalized_query', models.CharField(db_index=True, max_length=100)),
                ('search_count', models.PositiveIntegerField(default=1)),
                ('last_searched_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'search_searchquerylog',
                'verbose_name': 'Search Query Log',
                'verbose_name_plural': 'Search Query Logs',
                'ordering': ['-search_count'],
            },
        ),
        migrations.AddIndex(
            model_name='searchquerylog',
            index=models.Index(fields=['normalized_query'], name='search_sql_norm_idx'),
        ),
        migrations.AddIndex(
            model_name='searchquerylog',
            index=models.Index(fields=['-search_count'], name='search_sql_count_idx'),
        ),
    ]
