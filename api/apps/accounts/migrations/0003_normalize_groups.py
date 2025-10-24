# Blank data migration: groups are now seeded via `seed_groups` command per deployment

from django.db import migrations
from django.contrib.auth.models import Group


def normalize_groups_forward(apps, schema_editor):
    """No-op: group provisioning is handled by seed_groups management command."""
    return


def normalize_groups_reverse(apps, schema_editor):
    """No-op reverse."""
    return


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_alter_user_email'),
    ]

    operations = [
        migrations.RunPython(
            normalize_groups_forward,
            reverse_code=normalize_groups_reverse
        ),
    ]
