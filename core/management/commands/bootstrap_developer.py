from getpass import getpass

from django.core.management.base import BaseCommand, CommandError

from core.security import password_validation_errors, set_password
from developer.models import Developer


class Command(BaseCommand):
    help = "Create or reset a FaceMate developer account with a hashed password."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Developer email address")
        parser.add_argument("--name", required=True, help="Developer display name")

    def handle(self, *args, **options):
        password = getpass("Password: ")
        confirmation = getpass("Password (again): ")
        if not password:
            raise CommandError("Password cannot be empty.")
        if password != confirmation:
            raise CommandError("Passwords did not match.")
        password_errors = password_validation_errors(password)
        if password_errors:
            raise CommandError(" ".join(password_errors))

        developer, created = Developer.objects.get_or_create(
            email=options["email"].strip().lower(),
            defaults={"name": options["name"].strip(), "password": ""},
        )
        developer.name = options["name"].strip()
        set_password(developer, password)
        developer.save(update_fields=["name", "password"])
        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} developer account for {developer.email}."))
