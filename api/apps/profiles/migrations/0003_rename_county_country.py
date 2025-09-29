# Generated manually for renaming county to country

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0002_profile_bio_profile_city_profile_county'),
    ]

    operations = [
        migrations.RenameField(
            model_name='profile',
            old_name='county',
            new_name='country',
        ),
    ]
