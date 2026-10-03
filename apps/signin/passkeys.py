"""Passkey ceremonies: django-otp-webauthn's JSON views, held to Kosha's rules."""

from typing import TYPE_CHECKING

from django.contrib.auth.decorators import login_not_required
from django_otp_webauthn import exceptions, views

from apps.signin import confirmation, security_log, ways
from apps.signin.middleware import part_of_signing_in
from apps.signin.pause import refused_while_paused

if TYPE_CHECKING:
    from django.http import JsonResponse
    from django_otp_webauthn.models import AbstractWebAuthnCredential


class ConfirmFirst(exceptions.OTPWebAuthnApiError):
    """Only the first Way to sign in is added without a Confirmation."""

    status_code = 403
    default_detail = "Confirm it's you before adding a passkey."
    default_code = "confirm_first"


class FirstOrConfirmed:
    """Add the first Passkey freely, and later ones only once confirmed.

    The ceremony is reachable on the password alone, so someone holding only a
    stolen password must not be able to add their own Passkey.
    """

    def check_can_register(self) -> None:
        """Refuse an Owner who has a Way to sign in but hasn't confirmed it's them.

        Raises:
            ConfirmFirst: There is no Confirmation.
        """
        request = self.request
        if ways.has_way_to_sign_in(request.user) and not confirmation.is_open(request):
            raise ConfirmFirst


class BeginRegistration(FirstOrConfirmed, views.BeginCredentialRegistrationView):
    """Start adding a Passkey."""


class CompleteRegistration(FirstOrConfirmed, views.CompleteCredentialRegistrationView):
    """Save the new Passkey; the first also finishes signing in."""

    def post(self, *args: object, **kwargs: object) -> JsonResponse:
        """Save the Passkey as the library does, and log it.

        A first Passkey finishes signing in, so it opens a Confirmation.

        Args:
            *args: Positional URL arguments.
            **kwargs: Keyword URL arguments.

        Returns:
            The new Passkey's id.
        """
        signing_in = not self.request.user.is_verified()
        response = super().post(*args, **kwargs)
        if signing_in:
            confirmation.start(self.request)
        security_log.record(self.request, security_log.Kind.PASSKEY_ADDED)
        return response


class CompleteSignIn(views.CompleteCredentialAuthenticationView):
    """Sign in with a Passkey alone or after the password, or Confirm it's you."""

    def complete_auth(self, device: AbstractWebAuthnCredential) -> None:
        """Sign in as the library does, opening a Confirmation, and log how.

        Args:
            device: The Passkey just used.
        """
        owner = self.request.user
        # Already signed in, the Passkey only confirms it's them.
        signing_in = not owner.is_verified()
        how = "Password and passkey" if owner.is_authenticated else "Passkey"
        super().complete_auth(device)
        confirmation.start(self.request)
        if signing_in:
            security_log.signed_in(self.request, how)


register_begin = part_of_signing_in(BeginRegistration.as_view())
register_complete = part_of_signing_in(CompleteRegistration.as_view())
# Public, since a Passkey signs in on its own.
sign_in_begin = login_not_required(
    part_of_signing_in(views.BeginCredentialAuthenticationView.as_view())
)
# django-axes refuses a paused address inside the library's sign-in, which
# would fail on it; refusing first shows the paused page instead.
sign_in_complete = login_not_required(
    part_of_signing_in(refused_while_paused(CompleteSignIn.as_view()))
)
