"""Passkey ceremonies: django-otp-webauthn's JSON views, held to Kosha's rules."""

from django.contrib.auth.decorators import login_not_required
from django_otp_webauthn import exceptions, views

from apps.signin import ways
from apps.signin.middleware import part_of_signing_in


class AlreadyHasWay(exceptions.OTPWebAuthnApiError):
    """Only the first Way to sign in is added outside Security."""

    status_code = 403
    default_detail = "You already have a way to sign in."
    default_code = "already_has_way"


class FirstWayOnly:
    """Refuse a Passkey once the Owner has any Way to sign in.

    The ceremony is reachable on the password alone, so someone holding only a
    stolen password must not be able to add their own Passkey.
    """

    def check_can_register(self) -> None:
        """Refuse an Owner who already has a Way to sign in.

        Raises:
            AlreadyHasWay: The Owner already has a Way to sign in.
        """
        if ways.has_way_to_sign_in(self.request.user):
            raise AlreadyHasWay


class BeginRegistration(FirstWayOnly, views.BeginCredentialRegistrationView):
    """Start adding a Passkey."""


class CompleteRegistration(FirstWayOnly, views.CompleteCredentialRegistrationView):
    """Save the new Passkey, which also finishes signing in."""


register_begin = part_of_signing_in(BeginRegistration.as_view())
register_complete = part_of_signing_in(CompleteRegistration.as_view())
# Public, since a Passkey signs in on its own.
sign_in_begin = login_not_required(
    part_of_signing_in(views.BeginCredentialAuthenticationView.as_view())
)
sign_in_complete = login_not_required(
    part_of_signing_in(views.CompleteCredentialAuthenticationView.as_view())
)
