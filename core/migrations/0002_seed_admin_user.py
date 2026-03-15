from django.db import migrations
from django.contrib.auth.hashers import make_password


def create_default_admin(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    username = 'admin'
    password = 'R4h4s1a1'

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'is_staff': True,
            'is_superuser': True,
            'is_active': True,
            'email': 'admin@localhost.local',
        },
    )

    if created:
        user.password = make_password(password)
        user.save(update_fields=['password'])
    else:
        changed = False
        if not user.is_staff:
            user.is_staff = True
            changed = True
        if not user.is_superuser:
            user.is_superuser = True
            changed = True
        if not user.is_active:
            user.is_active = True
            changed = True

        # enforce requested credential for local admin account
        user.password = make_password(password)
        changed = True

        if changed:
            user.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(create_default_admin, noop),
    ]
