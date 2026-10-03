"""Claiming the install, and signing in and out."""

from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.urls import path

from apps.signin import passkeys, views

urlpatterns = [
    path("claim/", views.claim, name="claim"),
    path("claim/owner/", views.claim_owner, name="claim_owner"),
    path("way-to-sign-in/", views.choose_way, name="choose_way"),
    path(
        "way-to-sign-in/authenticator/",
        views.set_up_authenticator,
        name="set_up_authenticator",
    ),
    path(
        "way-to-sign-in/passkey/begin/",
        passkeys.register_begin,
        name="passkey_register_begin",
    ),
    path(
        "way-to-sign-in/passkey/complete/",
        passkeys.register_complete,
        name="passkey_register_complete",
    ),
    path("recovery-codes/", views.recovery_codes, name="recovery_codes"),
    path("sign-in/", login_not_required(views.SignInView.as_view()), name="sign_in"),
    path("sign-in/code/", views.code_step, name="code_step"),
    path(
        "sign-in/passkey/begin/",
        passkeys.sign_in_begin,
        name="passkey_sign_in_begin",
    ),
    path(
        "sign-in/passkey/complete/",
        passkeys.sign_in_complete,
        name="passkey_sign_in_complete",
    ),
    # Public so a page left open past its sign-in can still sign out cleanly.
    path(
        "sign-out/",
        login_not_required(auth_views.LogoutView.as_view()),
        name="sign_out",
    ),
]
