from django.db import migrations


def verify_existing_users(apps, schema_editor):
    """Mark all pre-existing users as email_verified=True.
    These are seeded demo accounts — they have no real inbox to verify from."""
    User = apps.get_model('users', 'User')
    User.objects.all().update(email_verified=True)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_add_email_verification_fields'),
    ]

    operations = [
        migrations.RunPython(verify_existing_users, migrations.RunPython.noop),
    ]
