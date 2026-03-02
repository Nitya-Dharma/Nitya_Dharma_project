# Generated manually to add category field to Pooja model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masterdata', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='pooja',
            name='category',
            field=models.CharField(
                blank=True,
                choices=[
                    ('daily_household', 'A. Daily & Common Household Poojas'),
                    ('house_property_vehicle', 'B. House, Property & Vehicle Poojas'),
                    ('life_samskaras', 'C. Important Life Samskaras'),
                    ('festival_temple', 'D. Festival & Temple Poojas'),
                    ('homams', 'E. Homams / Fire Rituals'),
                    ('yagnas', 'F. Yagnas'),
                ],
                help_text='Category this pooja belongs to (authoritative list)',
                max_length=50,
                null=True,
                verbose_name='Category'
            ),
        ),
        migrations.AlterField(
            model_name='pooja',
            name='name',
            field=models.CharField(
                help_text='Name of the pooja type (e.g., Ganapati Puja, Satyanarayana Vratam)',
                max_length=100,
                unique=True,
                verbose_name='Pooja Name'
            ),
        ),
        migrations.AlterModelOptions(
            name='pooja',
            options={
                'ordering': ['category', 'name'],
                'verbose_name': 'Pooja',
                'verbose_name_plural': 'Poojas',
            },
        ),
    ]












