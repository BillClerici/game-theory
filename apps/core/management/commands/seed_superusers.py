from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

SUPERUSERS = [
    {"email": "wildbill.clerici@gmail.com", "password": "admin123", "first_name": "Bill", "last_name": "Clerici"},
    {"email": "bill@1200investing.com", "password": "admin123", "first_name": "Bill", "last_name": "Clerici"},
]


class Command(BaseCommand):
    help = "Create default superuser accounts (idempotent - skips existing)"

    def handle(self, *args, **options):
        for user_data in SUPERUSERS:
            email = user_data["email"]
            existing = User.objects.filter(email=email).first()
            if existing:
                # Ensure existing user has superuser privileges
                updated = []
                if not existing.is_superuser:
                    existing.is_superuser = True
                    updated.append("is_superuser")
                if not existing.is_staff:
                    existing.is_staff = True
                    updated.append("is_staff")
                if updated:
                    existing.save(update_fields=updated)
                    self.stdout.write(self.style.WARNING(f"  [~] {email} already exists - promoted to superuser"))
                else:
                    self.stdout.write(f"  [=] {email} already exists - OK")
                continue
            user = User.objects.create_superuser(
                email=email,
                first_name=user_data.get("first_name", ""),
                last_name=user_data.get("last_name", ""),
            )
            # Set password for admin access (superusers are the only exception to no-password rule)
            user.set_password(user_data["password"])
            user.save(update_fields=["password"])
            self.stdout.write(self.style.SUCCESS(f"  [+] Created superuser: {email}"))
