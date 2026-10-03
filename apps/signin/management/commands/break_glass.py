"""Let the Owner back in from the server when every Way to sign in is lost."""

from axes.utils import reset as lift_every_pause
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.utils.crypto import get_random_string
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp_webauthn.models import WebAuthnCredential

from apps.signin import security_log

# Lower case without look-alikes (i, l, o), easy to type on a phone.
LETTERS = "abcdefghjkmnpqrstuvwxyz"


class Command(BaseCommand):
    """Reset the Ways to sign in, the password, or both."""

    help = (
        "Reset the Ways to sign in and/or the password, sign out every Session "
        "and lift every Pause."
    )

    def add_arguments(self, parser: CommandParser) -> None:  # ruff: ignore[no-self-use]
        """Choose what to reset.

        Args:
            parser: The command's argument parser.
        """
        parser.add_argument(
            "--ways-to-sign-in",
            action="store_true",
            help="Remove every Passkey, the Authenticator app and the Recovery "
            "codes. The password alone then signs in, straight to setting up a "
            "new Way to sign in.",
        )
        parser.add_argument(
            "--password",
            action="store_true",
            help="Set a new random password and print it.",
        )

    @transaction.atomic
    def handle(self, *args: object, **options: object) -> None:  # ruff: ignore[unused-method-argument]
        """Reset what was chosen.

        Raises:
            CommandError: Nothing was chosen, or there is no Owner yet.
        """
        ways, password = options["ways_to_sign_in"], options["password"]
        if not ways and not password:
            msg = "Choose what to reset: --ways-to-sign-in, --password or both."
            raise CommandError(msg)
        owner = get_user_model().objects.first()
        if owner is None:
            msg = "Kosha isn't claimed yet; there's nothing to reset."
            raise CommandError(msg)

        reset, report = [], []
        if ways:
            for model in (TOTPDevice, StaticDevice, WebAuthnCredential):
                model.objects.filter(user=owner).delete()
            reset.append("Ways to sign in")
            report.append(
                "Ways to sign in removed: sign in with the password to set one up."
            )
        if password:
            new_password = "-".join(get_random_string(4, LETTERS) for _ in range(4))
            owner.set_password(new_password)
            owner.save(update_fields=["password"])
            reset.append("password")
            report.append(f"New password: {new_password}  (change it once signed in)")

        # The Owner is the only login, so every session is theirs.
        Session.objects.all().delete()
        lift_every_pause()
        security_log.record(
            None, security_log.Kind.RESET_ON_SERVER, " and ".join(reset).capitalize()
        )
        report.append("Every Session is signed out and every Pause lifted.")
        # Printed only once nothing is left to fail, so a password is never
        # shown that the rollback undid.
        self.stdout.write("\n".join(report))
