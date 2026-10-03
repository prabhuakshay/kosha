"""Print the Setup code for an unclaimed install."""

from django.core.management.base import BaseCommand

from apps.signin.claim import is_claimed, setup_code


class Command(BaseCommand):
    """Print the code that Claims this install, while it has no Owner."""

    help = "Print the Setup code that Claims this install, while it has no Owner."

    def handle(self, *args: object, **options: object) -> None:  # ruff: ignore[unused-method-argument]
        """Print the code, or say the install is already claimed."""
        if is_claimed():
            self.stdout.write("Kosha is claimed; there is no Setup code.")
        else:
            self.stdout.write(f"Setup code: {setup_code()}  (enter it to claim Kosha)")
