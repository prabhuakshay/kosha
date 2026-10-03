import pytest
from django.contrib.sessions.models import Session
from django.test import Client
from django.urls import reverse
from django_otp.plugins.otp_static.models import StaticDevice

from apps.core.testing import EMAIL, PASSWORD, tags
from apps.signin.models import SecurityLogEntry
from apps.signin.testing import (
    add_passkey,
    add_recovery_code,
    authenticator_code,
    enter_code,
    shown_codes,
    sign_in,
    sign_in_with_passkey,
)

Kind = SecurityLogEntry.Kind
SECURITY = reverse("security")
NEW_PASSWORD = "a quiet copper meadow"  # ruff: ignore[hardcoded-password-string]


def links(response, name):
    return tags(response, "a", href=reverse(name))


def logged(kind):
    return SecurityLogEntry.objects.filter(kind=kind).count()


@pytest.mark.django_db
def test_security_lists_how_kosha_is_signed_in_to(signed_in):
    response = signed_in.get(SECURITY)

    assert "None yet" in response.text
    assert "Authenticator app" in response.text
    assert ">On<" in response.text
    assert "0 of 10 left" in response.text
    assert links(response, "password")
    assert links(response, "sessions")
    assert links(response, "security_log")


@pytest.mark.django_db
@pytest.mark.usefixtures("browser")
def test_security_lists_the_passkeys(client, owner):
    for name in ("Pixel 9", "MacBook"):
        add_passkey(owner, name)
    add_recovery_code(owner)
    sign_in_with_passkey(client)

    response = client.get(SECURITY)

    assert "2 passkeys" in response.text
    assert ">Pixel 9<" in response.text
    assert ">MacBook<" in response.text
    assert ">Off<" in response.text
    assert "1 of 10 left" in response.text


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["password", "sessions", "security_log"])
def test_every_security_screen_needs_a_confirmation(signed_in, clock, name):
    clock.advance(minutes=11)

    response = signed_in.get(reverse(name))

    assert response["Location"] == f"{reverse('confirm')}?next={reverse(name)}"


def change_password(client, new=NEW_PASSWORD):
    return client.post(
        reverse("password"), {"new_password1": new, "new_password2": new}
    )


@pytest.mark.django_db
def test_change_the_password(signed_in, owner):
    response = change_password(signed_in)

    assert response["Location"] == SECURITY
    owner.refresh_from_db()
    assert owner.check_password(NEW_PASSWORD)
    assert logged(Kind.PASSWORD_CHANGED) == 1


@pytest.mark.django_db
def test_changing_the_password_keeps_this_session_and_signs_out_the_others(
    signed_in, owner, authenticator
):
    elsewhere = Client()
    sign_in(elsewhere)
    enter_code(elsewhere, authenticator_code(authenticator.bin_key, steps_ahead=1))

    change_password(signed_in)

    assert signed_in.get(SECURITY).status_code == 200
    assert Session.objects.count() == 1
    assert elsewhere.get(reverse("home"))["Location"].startswith(reverse("sign_in"))


@pytest.mark.django_db
@pytest.mark.usefixtures("browser")
def test_a_forgotten_password_is_changed_after_signing_in_with_a_passkey(client, owner):
    add_passkey(owner)
    sign_in_with_passkey(client)

    response = change_password(client)

    assert response["Location"] == SECURITY
    owner.refresh_from_db()
    assert owner.check_password(NEW_PASSWORD)


@pytest.mark.django_db
def test_a_weak_new_password_is_refused(signed_in, owner):
    response = change_password(signed_in, new=EMAIL)

    assert response.status_code == 200
    owner.refresh_from_db()
    assert owner.check_password(PASSWORD)


@pytest.mark.django_db
def test_make_new_recovery_codes(signed_in, owner):
    add_recovery_code(owner)

    response = signed_in.post(reverse("make_recovery_codes"))

    assert response["Location"] == reverse("new_recovery_codes")
    codes = shown_codes(signed_in.get(response["Location"]))
    assert len(set(codes)) == 10
    assert "k7m2 x9qa" not in codes
    assert logged(Kind.RECOVERY_CODES_ISSUED) == 1


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_new_recovery_codes_work_and_the_old_ones_stop(signed_in, owner):
    add_recovery_code(owner)
    response = signed_in.post(reverse("make_recovery_codes"), follow=True)
    [new_code, *_] = shown_codes(response)
    other = Client()

    sign_in(other)
    enter_code(other, new_code)
    assert other.get(reverse("home")).status_code == 200
    other.post(reverse("sign_out"))
    sign_in(other)
    assert "That code doesn&#x27;t match." in enter_code(other, "k7m2x9qa").text


@pytest.mark.django_db
def test_new_recovery_codes_are_shown_once(signed_in):
    signed_in.post(reverse("make_recovery_codes"))
    signed_in.get(reverse("new_recovery_codes"))

    response = signed_in.get(reverse("new_recovery_codes"))

    assert response["Location"] == SECURITY


@pytest.mark.django_db
def test_new_recovery_codes_are_made_only_by_a_post(signed_in):
    response = signed_in.get(reverse("make_recovery_codes"))

    assert response.status_code == 405
    assert not StaticDevice.objects.exists()
