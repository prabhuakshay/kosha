import re

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import dateformat, timezone
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp_webauthn.models import WebAuthnCredential

from apps.core.testing import tags
from apps.signin.models import SecurityLogEntry
from apps.signin.testing import (
    add_passkey,
    authenticator_code,
    claim,
    enter_code,
    register_passkey,
    replace_authenticator,
    set_up_authenticator,
    shown_key,
    sign_in,
    sign_in_with_passkey,
)

pytestmark = pytest.mark.usefixtures("browser")

Kind = SecurityLogEntry.Kind
SECURITY = reverse("security")
CONFIRM_FIRST = f"{reverse('confirm')}?next={SECURITY}"


def logged(kind):
    return SecurityLogEntry.objects.filter(kind=kind).count()


def day(at):
    return dateformat.format(timezone.localtime(at), "j M Y")


def remove_passkey(client, passkey):
    return client.post(reverse("remove_passkey", args=[passkey.pk]))


def remove_authenticator(client):
    return client.post(reverse("remove_authenticator"))


@pytest.fixture
def passkey_only(client, owner):
    """The Owner's only Way to sign in, a Passkey the client signed in by."""
    passkey = add_passkey(owner)
    sign_in_with_passkey(client)
    return passkey


@pytest.mark.django_db
def test_security_offers_to_add_a_passkey(signed_in):
    response = signed_in.get(SECURITY)

    [button] = tags(response, "button", **{"data-passkey": "register"})
    assert button["data-next"] == SECURITY


@pytest.mark.django_db
def test_add_a_passkey(signed_in):
    assert register_passkey(signed_in).status_code == 200

    assert WebAuthnCredential.objects.count() == 1
    assert logged(Kind.PASSKEY_ADDED) == 1


@pytest.mark.django_db
def test_adding_a_passkey_needs_a_confirmation(signed_in, clock):
    clock.advance(minutes=11)

    response = register_passkey(signed_in)

    assert response.status_code == 403
    assert "Confirm it" in response.json()["detail"]
    assert not WebAuthnCredential.objects.exists()


@pytest.mark.django_db
def test_claiming_with_a_passkey_logs_it(client):
    claim(client)
    register_passkey(client)

    assert logged(Kind.PASSKEY_ADDED) == 1


@pytest.mark.django_db
def test_passkeys_are_listed_newest_first_with_when_added_and_last_used(
    signed_in, owner, clock
):
    older = add_passkey(owner, "MacBook")
    clock.advance(days=2)
    newer = add_passkey(owner, "Pixel 9")
    clock.advance(days=3)
    # Confirms with the first Passkey, so it's been used today.
    sign_in_with_passkey(signed_in)

    response = signed_in.get(SECURITY)

    assert re.findall(r"data-passkey-name>([^<]+)<", response.text) == [
        "Pixel 9",
        "MacBook",
    ]
    assert f"Added {day(newer.created_at)} · Never used" in response.text
    assert f"Added {day(older.created_at)} · Last used {day(clock.now)}" in (
        response.text
    )


@pytest.mark.django_db
def test_remove_a_passkey(signed_in, owner):
    passkey = add_passkey(owner)

    response = remove_passkey(signed_in, passkey)

    assert response["Location"] == SECURITY
    assert not WebAuthnCredential.objects.exists()
    assert logged(Kind.PASSKEY_REMOVED) == 1
    assert "Passkey removed." in signed_in.get(SECURITY).text


@pytest.mark.django_db
def test_removing_a_passkey_needs_a_confirmation(signed_in, owner, clock):
    passkey = add_passkey(owner)
    clock.advance(minutes=11)

    response = remove_passkey(signed_in, passkey)

    assert response["Location"] == CONFIRM_FIRST
    assert WebAuthnCredential.objects.exists()


@pytest.mark.django_db
def test_a_passkey_is_removed_only_by_a_post(signed_in, owner):
    passkey = add_passkey(owner)

    response = signed_in.get(reverse("remove_passkey", args=[passkey.pk]))

    assert response.status_code == 405
    assert WebAuthnCredential.objects.exists()


@pytest.mark.django_db
def test_removing_the_passkey_signed_in_with_stays_signed_in(client, owner):
    used = add_passkey(owner, "MacBook")
    add_passkey(owner, "Pixel 9")
    sign_in_with_passkey(client)

    remove_passkey(client, used)

    assert client.get(reverse("home")).status_code == 200


@pytest.mark.django_db
def test_removing_the_last_passkey_is_refused(client, passkey_only):
    response = remove_passkey(client, passkey_only)

    assert response["Location"] == SECURITY
    assert (
        "This is your only way to sign in. Add another passkey or an authenticator "
        "app first, then remove it."
    ) in client.get(SECURITY).text
    assert WebAuthnCredential.objects.exists()
    assert logged(Kind.PASSKEY_REMOVED) == 0


@pytest.mark.django_db
def test_security_offers_to_set_up_an_authenticator_app(client, passkey_only):
    response = client.get(SECURITY)

    assert tags(response, "form", action=reverse("start_authenticator"))
    assert "Set up" in response.text
    assert not tags(response, "form", action=reverse("remove_authenticator"))


@pytest.mark.django_db
def test_set_up_an_authenticator_app(client, passkey_only):
    response = replace_authenticator(client)

    assert response["Location"] == SECURITY
    assert TOTPDevice.objects.filter(confirmed=True).count() == 1
    assert logged(Kind.AUTHENTICATOR_SET_UP) == 1
    assert "Authenticator app set up." in client.get(SECURITY).text


@pytest.mark.django_db
def test_security_offers_to_replace_or_remove_the_authenticator_app(signed_in):
    response = signed_in.get(SECURITY)

    assert tags(response, "form", action=reverse("start_authenticator"))
    assert tags(response, "form", action=reverse("remove_authenticator"))
    assert "Replace with a new one" in response.text


@pytest.mark.django_db
def test_replace_the_authenticator_app_staying_signed_in(signed_in, authenticator):
    response = replace_authenticator(signed_in)

    assert response["Location"] == SECURITY
    assert TOTPDevice.objects.get().key != authenticator.key
    assert signed_in.get(reverse("home")).status_code == 200
    assert logged(Kind.AUTHENTICATOR_SET_UP) == 1
    elsewhere = Client()
    sign_in(elsewhere)
    old_code = authenticator_code(authenticator.bin_key, steps_ahead=1)
    assert "That code doesn&#x27;t match." in enter_code(elsewhere, old_code).text


@pytest.mark.django_db
def test_a_wrong_code_keeps_the_old_authenticator_app(signed_in, authenticator):
    response = replace_authenticator(signed_in, "000000")

    assert response.status_code == 200
    assert "That code doesn&#x27;t match." in response.text
    assert TOTPDevice.objects.get() == authenticator
    assert logged(Kind.AUTHENTICATOR_SET_UP) == 0


@pytest.mark.django_db
def test_the_key_stays_the_same_across_reloads(signed_in):
    signed_in.post(reverse("start_authenticator"))
    first = shown_key(signed_in.get(reverse("new_authenticator")))

    assert shown_key(signed_in.get(reverse("new_authenticator"))) == first


@pytest.mark.django_db
def test_back_after_finishing_a_setup_does_not_start_another(signed_in):
    replace_authenticator(signed_in)

    response = signed_in.get(reverse("new_authenticator"))

    assert response["Location"] == SECURITY


@pytest.mark.django_db
def test_a_setup_starts_only_by_a_post(signed_in):
    assert signed_in.get(reverse("start_authenticator")).status_code == 405
    assert signed_in.get(reverse("new_authenticator"))["Location"] == SECURITY


@pytest.mark.django_db
def test_setting_up_an_authenticator_app_needs_a_confirmation(signed_in, clock):
    clock.advance(minutes=11)

    response = signed_in.post(reverse("start_authenticator"))

    assert response["Location"] == CONFIRM_FIRST


@pytest.mark.django_db
def test_claiming_with_an_authenticator_app_logs_it(client):
    claim(client)
    set_up_authenticator(client)

    assert logged(Kind.AUTHENTICATOR_SET_UP) == 1


@pytest.mark.django_db
def test_remove_the_authenticator_app_staying_signed_in(signed_in, owner):
    add_passkey(owner)

    response = remove_authenticator(signed_in)

    assert response["Location"] == SECURITY
    assert not TOTPDevice.objects.exists()
    assert logged(Kind.AUTHENTICATOR_REMOVED) == 1
    assert signed_in.get(reverse("home")).status_code == 200
    assert "Authenticator app removed." in signed_in.get(SECURITY).text


@pytest.mark.django_db
def test_removing_the_authenticator_app_needs_a_confirmation(signed_in, owner, clock):
    add_passkey(owner)
    clock.advance(minutes=11)

    response = remove_authenticator(signed_in)

    assert response["Location"] == CONFIRM_FIRST
    assert TOTPDevice.objects.exists()


@pytest.mark.django_db
def test_removing_the_only_authenticator_app_is_refused(signed_in):
    response = remove_authenticator(signed_in)

    assert response["Location"] == SECURITY
    assert (
        "This is your only way to sign in. Add a passkey first, then remove it."
    ) in signed_in.get(SECURITY).text
    assert TOTPDevice.objects.exists()
    assert logged(Kind.AUTHENTICATOR_REMOVED) == 0


@pytest.mark.django_db
def test_removing_an_authenticator_app_there_isnt_is_not_found(client, owner):
    add_passkey(owner, "MacBook")
    add_passkey(owner, "Pixel 9")
    sign_in_with_passkey(client)

    assert remove_authenticator(client).status_code == 404
