# Migration to normalize group names for TalentCo
# Updates existing groups and creates normalized group structure

from django.db import migrations
from django.contrib.auth.models import Group


def normalize_groups_forward(apps, schema_editor):
    """Normalize group names and create missing groups."""
    Group = apps.get_model('auth', 'Group')

    # Mapping of old names to new normalized names
    group_mapping = {
        'job_seeking': 'candidate',
        'hiring': 'employer',
        'system_administration': 'administrator',
    }

    # Update existing groups
    for old_name, new_name in group_mapping.items():
        try:
            group = Group.objects.get(name=old_name)
            group.name = new_name
            group.save()
            print(f"Updated group '{old_name}' to '{new_name}'")
        except Group.DoesNotExist:
            print(f"Group '{old_name}' not found, skipping update")

    # Create any missing normalized groups
    normalized_groups = [
        ('candidate', 'Job seekers and candidates looking for employment opportunities'),
        ('employer', 'Companies and organizations posting jobs and hiring talent'),
        ('recruiter', 'Recruitment professionals and talent partners'),
        ('administrator', 'System administrators with full platform access'),
    ]

    for name, description in normalized_groups:
        group, created = Group.objects.get_or_create(
            name=name,
            defaults={'name': name}
        )
        if created:
            print(f"Created group '{name}'")
        else:
            print(f"Group '{name}' already exists")


def normalize_groups_reverse(apps, schema_editor):
    """Reverse migration - restore old group names."""
    Group = apps.get_model('auth', 'Group')

    # Reverse mapping
    reverse_mapping = {
        'candidate': 'job_seeking',
        'employer': 'hiring',
        'administrator': 'system_administration',
    }

    # Update groups back to old names
    for new_name, old_name in reverse_mapping.items():
        try:
            group = Group.objects.get(name=new_name)
            group.name = old_name
            group.save()
            print(f"Reverted group '{new_name}' back to '{old_name}'")
        except Group.DoesNotExist:
            print(f"Group '{new_name}' not found, skipping revert")

    # Remove recruiter group if it exists (it didn't exist before)
    try:
        recruiter_group = Group.objects.get(name='recruiter')
        recruiter_group.delete()
        print("Removed 'recruiter' group")
    except Group.DoesNotExist:
        print("'recruiter' group not found, nothing to remove")


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
