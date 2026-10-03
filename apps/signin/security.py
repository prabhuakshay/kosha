"""Security: Confirm it's you, then the Owner's Ways to sign in, password and codes."""

from typing import TYPE_CHECKING

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.signin import confirmation, pause, security_log, sessions, ways
from apps.signin.forms import CodeForm
from apps.signin.views import next_url

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

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
