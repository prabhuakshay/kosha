import re
from io import StringIO

import pytest
from axes.models import AccessAttempt
from django.contrib.sessions.models import Session
from django.core.management import CommandError, call_command
from django.test import Client
from django.urls import reverse
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp_webauthn.models import WebAuthnCredential

from apps.signin.models import SecurityLogEntry
from apps.signin.testing import add_passkey, sign_in


@pytest.fixture
def owner(owner, authenticator):
    add_passkey(owner)
    StaticDevice.objects.create(user=owner, name="Recovery codes").token_set.create(
        token="k7m2x9qa"
    )
    return owner


def break_glass(*args):
    out = StringIO()
    call_command("break_glass", *args, stdout=out)
    return out.getvalue()


def has_ways():
    return any(
        model.objects.exists()
        for model in (TOTPDevice, StaticDevice, WebAuthnCredential)
    )


@pytest.mark.django_db
@pytest.mark.usefixtures("owner")
def test_resetting_the_ways_to_sign_in_removes_them_all(client):
    break_glass("--ways-to-sign-in")

    assert not has_ways()
    sign_in(client)
    assert client.get(reverse("home"))["Location"].startswith(reverse("choose_way"))


@pytest.mark.django_db
def test_resetting_the_password_prints_an_easy_to_type_one(client, owner):
    out = break_glass("--password")

    password = re.search(r"New password: (\S+)", out)[1]
    assert re.fullmatch(r"[a-hjkmnp-z]{4}(-[a-hjkmnp-z]{4}){3}", password)
    owner.refresh_from_db()
    assert owner.check_password(password)
    assert has_ways()


@pytest.mark.django_db
@pytest.mark.usefixtures("owner")
def test_both_can_be_reset_at_once():
    out = break_glass("--ways-to-sign-in", "--password")

    assert "New password: " in out
    assert not has_ways()
    assert SecurityLogEntry.objects.get().detail == "Ways to sign in and password"


@pytest.mark.django_db
def test_a_reset_signs_out_every_session_and_lifts_every_pause(signed_in):
    paused = Client(REMOTE_ADDR="203.0.113.9")
    for _ in range(5):
        sign_in(paused, password="not it")

    out = break_glass("--password")

    assert "Every Session is signed out and every Pause lifted." in out
    assert not Session.objects.exists()
    assert not AccessAttempt.objects.exists()
    assert signed_in.get(reverse("home")).status_code == 302
    assert paused.get(reverse("sign_in")).status_code == 200


@pytest.mark.django_db
@pytest.mark.usefixtures("owner")
@pytest.mark.parametrize(
    ("flag", "detail"),
    [("--ways-to-sign-in", "Ways to sign in"), ("--password", "Password")],
)
def test_a_reset_is_logged_as_reset_on_the_server(flag, detail):
    break_glass(flag)

    entry = SecurityLogEntry.objects.get()
    assert entry.kind == SecurityLogEntry.Kind.RESET_ON_SERVER
    assert entry.get_kind_display() == "Reset on the server"
    assert (entry.detail, entry.address, entry.device) == (detail, "", "")


@pytest.mark.django_db
def test_a_reset_that_fails_changes_nothing(signed_in, owner, monkeypatch):
    def fail(**kwargs):
        raise RuntimeError

    monkeypatch.setattr(SecurityLogEntry.objects, "create", fail)

    out = StringIO()
    with pytest.raises(RuntimeError):
        call_command("break_glass", "--ways-to-sign-in", "--password", stdout=out)

    assert not out.getvalue()
    assert has_ways()
    assert Session.objects.exists()
    owner.refresh_from_db()
    assert owner.check_password("a long harbour lantern")


@pytest.mark.django_db
@pytest.mark.usefixtures("owner")
def test_something_must_be_chosen():
    with pytest.raises(CommandError, match="--ways-to-sign-in"):
        break_glass()


@pytest.mark.django_db
def test_an_unclaimed_install_has_nothing_to_reset():
    with pytest.raises(CommandError, match="claimed"):
        break_glass("--password")
