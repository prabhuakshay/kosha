"""Claiming the install, and signing in and out."""

from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render, resolve_url
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django_otp import login as otp_login
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import default_key

from apps.signin import confirmation, pause, security_log, ways
from apps.signin.claim import is_claimed
from apps.signin.forms import (
    CodeForm,
    NewAuthenticatorForm,
    OwnerForm,
    SetupCodeForm,
)
from apps.signin.middleware import part_of_signing_in

if TYPE_CHECKING:
    from django.contrib.auth.forms import AuthenticationForm

# Passkeys add a backend, so signing in by password must name its own.
PASSWORD_BACKEND = "django.contrib.auth.backends.ModelBackend"  # ruff: ignore[hardcoded-password-string]
# Set once the Setup code is right, so step 2 can't be reached by URL.
CODE_ACCEPTED = "signin.setup_code_accepted"
# Kept until the app shows a right code, so reloading doesn't change the QR code.
AUTHENTICATOR_KEY = "signin.authenticator_key"


def next_url(request: HttpRequest) -> str:
    """Where to go on to: ``next``, unless it leads outside Kosha.

    Args:
        request: The incoming request.

    Returns:
        ``next``, or home.
    """
    url = request.GET.get("next", "")
    if url_has_allowed_host_and_scheme(
        url, {request.get_host()}, require_https=request.is_secure()
    ):
        return url
    return resolve_url(settings.LOGIN_REDIRECT_URL)


def _unclaimed_only() -> None:
    if is_claimed():
        raise Http404


@login_not_required
def claim(request: HttpRequest) -> HttpResponse:
    """Step 1 of Claim: the Setup code from the server's log.

    Args:
        request: The incoming request.

    Returns:
        The form, or a redirect to step 2 once the code is right.
    """
    _unclaimed_only()
    form = SetupCodeForm(request.POST or None)
    if form.is_valid():
        request.session[CODE_ACCEPTED] = True
        return redirect("claim_owner")
    return render(request, "signin/claim.html", {"form": form})


@login_not_required
def claim_owner(request: HttpRequest) -> HttpResponse:
    """Step 2 of Claim: the Owner's name, email and password.

    Args:
        request: The incoming request.

    Returns:
        The form, or a redirect home signed in once the Owner exists.
    """
    _unclaimed_only()
    if not request.session.get(CODE_ACCEPTED):
        return redirect("claim")
    form = OwnerForm(request.POST or None)
    if form.is_valid():
        login(request, form.save(), backend=PASSWORD_BACKEND)
        security_log.signed_in(request, "Password")
        return redirect("choose_way")
    return render(request, "signin/claim_owner.html", {"form": form})


@part_of_signing_in
def choose_way(request: HttpRequest) -> HttpResponse:
    """Step 3 of Claim: choose a Way to sign in.

    Args:
        request: The incoming request.

    Returns:
        The choice, or a redirect home once there is a Way to sign in.
    """
    if ways.has_way_to_sign_in(request.user):
        return redirect("home")
    return render(request, "signin/choose_way.html")


@part_of_signing_in
def set_up_authenticator(request: HttpRequest) -> HttpResponse:
    """Set up the Authenticator app as the first Way to sign in.

    Args:
        request: The incoming request.

    Returns:
        The QR code and key, a redirect to the Recovery codes once the app
        shows a right code, or a redirect home once there is a Way to sign in.
    """
    # Reachable on the password alone, so it must never replace a Way to sign in.
    if ways.has_way_to_sign_in(request.user):
        return redirect("home")
    key = request.session.setdefault(AUTHENTICATOR_KEY, default_key())
    device = ways.new_authenticator(request.user, key)
    form = NewAuthenticatorForm(device, request.POST or None)
    if form.is_valid():
        del request.session[AUTHENTICATOR_KEY]
        otp_login(request, device)
        confirmation.start(request)
        security_log.record(request, security_log.Kind.AUTHENTICATOR_SET_UP)
        return redirect("recovery_codes")
    return render(
        request,
        "signin/set_up_authenticator.html",
        {"form": form, "qr": ways.qr_code(device), "key": ways.typed_key(device)},
    )


def recovery_codes(request: HttpRequest) -> HttpResponse:
    """Step 4 of Claim: the Recovery codes, shown this once.

    Args:
        request: The incoming request.

    Returns:
        The codes, or a redirect home once they have been issued.
    """
    if ways.has_recovery_codes(request.user):
        return redirect("home")
    codes = ways.issue_recovery_codes(request.user)
    return render(request, "signin/recovery_codes.html", {"codes": codes})


@part_of_signing_in
@pause.refused_while_paused
def code_step(request: HttpRequest) -> HttpResponse:
    """After the password, a Passkey or a code from the Authenticator app.

    A Recovery code stands in for the code.

    Args:
        request: The incoming request.

    Returns:
        The form, or a redirect on to ``next`` once signed in.
    """
    owner = request.user
    if owner.is_verified():
        return redirect(next_url(request))
    if not ways.has_way_to_sign_in(owner):
        return redirect("choose_way")
    form = CodeForm(owner, request.POST or None)
    if form.is_valid():
        otp_login(request, form.device)
        confirmation.start(request)
        code = "recovery" if isinstance(form.device, StaticDevice) else "authenticator"
        security_log.signed_in(request, f"Password and {code} code")
        return redirect(next_url(request))
    if form.is_bound:
        pause.wrong_code(request, owner)
    return render(
        request,
        "signin/code_step.html",
        {
            "form": form,
            "has_passkey": ways.has_passkey(owner),
            "has_authenticator": ways.authenticator(owner) is not None,
        },
    )


class SignInView(auth_views.LoginView):
    """Email and password. A signed-in Owner goes straight home."""

    template_name = "signin/sign_in.html"
    redirect_authenticated_user = True

    def dispatch(
        self, request: HttpRequest, *args: object, **kwargs: object
    ) -> HttpResponse:
        """Send an unclaimed install to Claim, since nobody can sign in yet.

        Args:
            request: The incoming request.
            *args: Positional URL arguments.
            **kwargs: Keyword URL arguments.

        Returns:
            The sign-in page, or a redirect to Claim.
        """
        if not is_claimed():
            return redirect("claim")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form: AuthenticationForm) -> HttpResponse:
        """Sign in, logging it when the password is all there is to sign in with.

        Args:
            form: The right email and password.

        Returns:
            A redirect on, to the code step or setting up a Way to sign in.
        """
        response = super().form_valid(form)
        if not ways.has_way_to_sign_in(form.get_user()):
            security_log.signed_in(self.request, "Password")
        return response

    def form_invalid(self, form: AuthenticationForm) -> HttpResponse:
        """Log the wrong email or password.

        Args:
            form: The wrong email or password.

        Returns:
            The form with its error.
        """
        security_log.failed(self.request, security_log.Kind.WRONG_PASSWORD)
        return super().form_invalid(form)


@login_not_required
def admin_login(request: HttpRequest) -> HttpResponse:
    """Send the admin's own sign-in to Kosha's, so it has only one way in.

    Args:
        request: The incoming request.

    Returns:
        A redirect to Kosha's sign-in, coming back to the admin after.
    """
    return auth_views.redirect_to_login(request.GET.get("next", reverse("admin:index")))
