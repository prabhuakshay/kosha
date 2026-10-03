"""Claiming the install, signing in and out, and Security."""

from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.urls import path

from apps.signin import passkeys, security, views
from apps.signin.pause import refused_while_paused

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
    path(
        "sign-in/",
        login_not_required(refused_while_paused(views.SignInView.as_view())),
        name="sign_in",
    ),
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
    path("confirm/", security.confirm, name="confirm"),
    path("security/", security.security, name="security"),
    path(
        "security/passkeys/<int:pk>/remove/",
        security.remove_passkey,
        name="remove_passkey",
    ),
    path(
        "security/authenticator/",
        security.start_authenticator,
        name="start_authenticator",
    ),
    path(
        "security/authenticator/new/",
        security.new_authenticator,
        name="new_authenticator",
    ),
    path(
        "security/authenticator/remove/",
        security.remove_authenticator,
        name="remove_authenticator",
    ),
    path("security/password/", security.password, name="password"),
    path(
        "security/recovery-codes/",
        security.make_recovery_codes,
        name="make_recovery_codes",
    ),
    path(
        "security/recovery-codes/new/",
        security.new_recovery_codes,
        name="new_recovery_codes",
    ),
    path("security/sessions/", security.signed_in_sessions, name="sessions"),
    path(
        "security/sessions/sign-out-others/",
        security.sign_out_others,
        name="sign_out_others",
    ),
    path("security/log/", security.log, name="security_log"),
    # Public so a page left open past its sign-in can still sign out cleanly.
    path(
        "sign-out/",
        login_not_required(auth_views.LogoutView.as_view()),
        name="sign_out",
    ),
]
