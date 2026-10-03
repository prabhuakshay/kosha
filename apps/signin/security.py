"""Security: Confirm it's you, then the Owner's Ways to sign in, password and codes."""

from typing import TYPE_CHECKING

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django_otp import login as otp_login
from django_otp.plugins.otp_totp.models import default_key

from apps.signin import confirmation, pause, security_log, sessions, ways
from apps.signin.forms import CodeForm, NewAuthenticatorForm
from apps.signin.views import AUTHENTICATOR_KEY, next_url

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse
    from django_otp.models import Device

# Held from making to showing, so a reload can't make another set.
NEW_RECOVERY_CODES = "signin.new_recovery_codes"


@pause.refused_while_paused
def confirm(request: HttpRequest) -> HttpResponse:
    """Confirm it's you with a Passkey or the Authenticator app, not a Recovery code.

    Args:
        request: The incoming request.

    Returns:
        The form, or a redirect on to ``next`` once confirmed or while still
        confirmed.
    """
    owner = request.user
    if request.method == "GET" and confirmation.is_open(request):
        return redirect(next_url(request))
    form = CodeForm(owner, request.POST or None, recovery=False)
    if form.is_valid():
        confirmation.start(request)
        return redirect(next_url(request))
    if form.is_bound:
        pause.wrong_code(request, owner)
    return render(
        request,
        "signin/confirm.html",
        {
            "form": form,
            "has_passkey": ways.has_passkey(owner),
            "has_authenticator": ways.authenticator(owner) is not None,
        },
    )


@confirmation.required
def security(request: HttpRequest) -> HttpResponse:
    """Passkeys, the Authenticator app, password, Recovery codes, Sessions and log.

    Args:
        request: The incoming request.

    Returns:
        The page.
    """
    owner = request.user
    return render(
        request,
        "signin/security.html",
        {
            "passkeys": ways.passkeys(owner),
            "authenticator": ways.authenticator(owner),
            "recovery_codes_left": ways.recovery_codes_left(owner),
            "recovery_codes_total": ways.RECOVERY_CODES,
        },
    )


@require_POST
@confirmation.required
def start_authenticator(request: HttpRequest) -> HttpResponse:
    """Begin setting up an Authenticator app, new or replacing the one there is.

    Args:
        request: The incoming request.

    Returns:
        A redirect to the setup, with a new key to scan.
    """
    request.session[AUTHENTICATOR_KEY] = default_key()
    return redirect("new_authenticator")


@confirmation.required
def new_authenticator(request: HttpRequest) -> HttpResponse:
    """Set up the Authenticator app, replacing any there was, staying signed in.

    Args:
        request: The incoming request.

    Returns:
        The QR code and key, or a redirect to Security once the app shows a
        right code, or when no setup was begun.
    """
    # A setup starts only by POST, so Back here after one finishes can't start another.
    key = request.session.get(AUTHENTICATOR_KEY)
    if key is None:
        return redirect("security")
    device = ways.new_authenticator(request.user, key)
    form = NewAuthenticatorForm(device, request.POST or None)
    if form.is_valid():
        del request.session[AUTHENTICATOR_KEY]
        # It replaced any old one, which may be what verified this session.
        otp_login(request, device)
        security_log.record(request, security_log.Kind.AUTHENTICATOR_SET_UP)
        messages.success(request, "Authenticator app set up.")
        return redirect("security")
    return render(
        request,
        "signin/new_authenticator.html",
        {"form": form, "qr": ways.qr_code(device), "key": ways.typed_key(device)},
    )


def _remove(
    request: HttpRequest, way: Device, kind: security_log.Kind, other: str
) -> None:
    owner = request.user
    with transaction.atomic():
        # Locked so two removals at once can't each leave the other as the last.
        get_user_model().objects.select_for_update().get(pk=owner.pk)
        if ways.count(owner) == 1:
            messages.error(
                request,
                f"This is your only way to sign in. Add {other} first, then remove it.",
            )
            return
        verified_by_it = owner.otp_device == way
        way.delete()
        security_log.record(request, kind)
    # Stay signed in by a Way to sign in that's still there.
    if verified_by_it:
        otp_login(request, ways.authenticator(owner) or ways.passkeys(owner).first())
    messages.success(request, f"{kind.label}.")


@require_POST
@confirmation.required
def remove_authenticator(request: HttpRequest) -> HttpResponse:
    """Remove the Authenticator app, unless nothing else would sign in.

    Args:
        request: The incoming request.

    Returns:
        A redirect to Security.

    Raises:
        Http404: There is no Authenticator app.
    """
    authenticator = ways.authenticator(request.user)
    if authenticator is None:
        raise Http404
    _remove(
        request, authenticator, security_log.Kind.AUTHENTICATOR_REMOVED, "a passkey"
    )
    return redirect("security")


@require_POST
@confirmation.required
def remove_passkey(request: HttpRequest, pk: int) -> HttpResponse:
    """Remove a Passkey, unless nothing else would sign in.

    Args:
        request: The incoming request.
        pk: The Passkey.

    Returns:
        A redirect to Security.
    """
    passkey = get_object_or_404(ways.passkeys(request.user), pk=pk)
    _remove(
        request,
        passkey,
        security_log.Kind.PASSKEY_REMOVED,
        "another passkey or an authenticator app",
    )
    return redirect("security")


@confirmation.required
def password(request: HttpRequest) -> HttpResponse:
    """Change the password, staying signed in here and signing out everywhere else.

    Args:
        request: The incoming request.

    Returns:
        The form, or a redirect to Security once changed.
    """
    form = PasswordChangeForm(request.user, request.POST or None)
    if form.is_valid():
        update_session_auth_hash(request, form.save())
        sessions.sign_out_others(request)
        security_log.record(request, security_log.Kind.PASSWORD_CHANGED)
        return redirect("security")
    return render(request, "signin/password.html", {"form": form})


@require_POST
@confirmation.required
def make_recovery_codes(request: HttpRequest) -> HttpResponse:
    """Replace the Recovery codes, holding the new ones to be shown once.

    Args:
        request: The incoming request.

    Returns:
        A redirect to the new codes.
    """
    request.session[NEW_RECOVERY_CODES] = ways.issue_recovery_codes(request.user)
    security_log.record(request, security_log.Kind.RECOVERY_CODES_ISSUED)
    return redirect("new_recovery_codes")


@confirmation.required
def new_recovery_codes(request: HttpRequest) -> HttpResponse:
    """The Recovery codes just made, shown this once.

    Args:
        request: The incoming request.

    Returns:
        The codes, or a redirect to Security once they have been shown.
    """
    codes = request.session.pop(NEW_RECOVERY_CODES, None)
    if codes is None:
        return redirect("security")
    return render(request, "signin/new_recovery_codes.html", {"codes": codes})


@confirmation.required
def signed_in_sessions(request: HttpRequest) -> HttpResponse:
    """Every Session signed in as the Owner.

    Args:
        request: The incoming request.

    Returns:
        The page.
    """
    return render(request, "signin/sessions.html")


@confirmation.required
def log(request: HttpRequest) -> HttpResponse:
    """The Security log.

    Args:
        request: The incoming request.

    Returns:
        The page.
    """
    return render(request, "signin/security_log.html")
