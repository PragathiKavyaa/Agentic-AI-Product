
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Temporarily recover the production Django admin account."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_ADMIN_USERNAME")
        password = os.environ.get("DJANGO_ADMIN_PASSWORD")
        recovery_enabled = os.environ.get("DJANGO_ADMIN_RECOVERY_ENABLED")

        if recovery_enabled != "true":
            raise CommandError("Admin recovery is not enabled.")

        if not username or not password:
            raise CommandError(
                "Set DJANGO_ADMIN_USERNAME and DJANGO_ADMIN_PASSWORD."
            )

        if len(password) < 12:
            raise CommandError("Use a password with at least 12 characters.")

        User = get_user_model()
        user, created = User.objects.get_or_create(username=username)

        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        action = "Created" if created else "Recovered"
        self.stdout.write(
            self.style.SUCCESS(f"{action} the Django admin account.")
        )
