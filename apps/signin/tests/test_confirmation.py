import pytest
from django.urls import reverse
from django_otp.plugins.otp_static.models import StaticDevice

from apps.signin.models import SecurityLogEntry
from apps.signin.testing import (
    add_passkey,
    add_recovery_code,
    authenticator_code,
    claim,
    enter_code,
    register_passkey,
    set_up_authenticator,
    sign_in,
    sign_in_with_passkey,
)

SECURITY = reverse("security")
WRONG_CODE = "000000"


@pytest.fixture
def confirmed_a_while_ago(signed_in, clock):
    """Signed in, but past the Confirmation that signing in opened."""
    clock.advance(minutes=11)
    return signed_in


def confirm(client, code, next_url=SECURITY):
    return client.post(f"{reverse('confirm')}?next={next_url}", {"code": code})


@pytest.mark.django_db
def test_security_asks_to_confirm_its_you(confirmed_a_while_ago):
    response = confirmed_a_while_ago.get(SECURITY)

    assert response["Location"] == f"{reverse('confirm')}?next={SECURITY}"
    response = confirmed_a_while_ago.get(response["Location"])
    assert "Confirm it's you" in response.text
    assert "A recovery code won't work here." in response.text


@pytest.mark.django_db
def test_an_authenticator_code_confirms(confirmed_a_while_ago, authenticator):
    # Signing in used this step's code, which can't be used twice.
    code = authenticator_code(authenticator.bin_key, steps_ahead=1)

    response = confirm(confirmed_a_while_ago, code)

    assert response["Location"] == SECURITY
    assert confirmed_a_while_ago.get(SECURITY).status_code == 200


@pytest.mark.django_db
@pytest.mark.usefixtures("browser")
def test_a_passkey_confirms_without_logging_a_sign_in(confirmed_a_while_ago, owner):
    add_passkey(owner)
    signed_in_before = SecurityLogEntry.objects.filter(
        kind=SecurityLogEntry.Kind.SIGNED_IN
    ).count()

    response = sign_in_with_passkey(confirmed_a_while_ago, SECURITY)

    assert response.json()["redirect_url"] == SECURITY
    assert confirmed_a_while_ago.get(SECURITY).status_code == 200
    assert (
        SecurityLogEntry.objects.filter(kind=SecurityLogEntry.Kind.SIGNED_IN).count()
        == signed_in_before
    )


@pytest.mark.django_db
def test_a_recovery_code_does_not_confirm(confirmed_a_while_ago, owner):
    add_recovery_code(owner)

    response = confirm(confirmed_a_while_ago, "k7m2 x9qa")

    assert "That code doesn&#x27;t match." in response.text
    assert confirmed_a_while_ago.get(SECURITY).status_code == 302
    # Refused, so it's still there to sign in with.
    assert StaticDevice.objects.get().token_set.exists()


@pytest.mark.django_db
def test_a_wrong_code_does_not_confirm(confirmed_a_while_ago):
    response = confirm(confirmed_a_while_ago, WRONG_CODE)

    assert response.status_code == 200
    assert "That code doesn&#x27;t match." in response.text
    assert confirmed_a_while_ago.get(SECURITY).status_code == 302


@pytest.mark.django_db
def test_wrong_codes_count_toward_the_pause(confirmed_a_while_ago):
    for _ in range(4):
        assert confirm(confirmed_a_while_ago, WRONG_CODE).status_code == 200

    assert confirm(confirmed_a_while_ago, WRONG_CODE).status_code == 429
    assert confirmed_a_while_ago.get(reverse("confirm")).status_code == 429
    assert (
        SecurityLogEntry.objects.filter(kind=SecurityLogEntry.Kind.WRONG_CODE).count()
        == 4
    )


@pytest.mark.django_db
def test_a_confirmation_lasts_10_minutes(confirmed_a_while_ago, authenticator, clock):
    confirm(confirmed_a_while_ago, authenticator_code(authenticator.bin_key, 1))

    clock.advance(minutes=9, seconds=59)
    assert confirmed_a_while_ago.get(SECURITY).status_code == 200
    clock.advance(seconds=1)
    assert confirmed_a_while_ago.get(SECURITY).status_code == 302


@pytest.mark.django_db
def test_confirm_goes_straight_on_while_confirmed(signed_in):
    response = signed_in.get(f"{reverse('confirm')}?next={SECURITY}")

    assert response["Location"] == SECURITY


@pytest.mark.django_db
def test_confirm_ignores_a_next_outside_kosha(signed_in):
    response = signed_in.get(f"{reverse('confirm')}?next=https://evil.example.com/")

    assert response["Location"] == reverse("home")


@pytest.mark.django_db
def test_a_change_asked_for_unconfirmed_comes_back_to_security(confirmed_a_while_ago):
    response = confirmed_a_while_ago.post(reverse("make_recovery_codes"))

    assert response["Location"] == f"{reverse('confirm')}?next={SECURITY}"
    assert not StaticDevice.objects.exists()


@pytest.mark.django_db
def test_signing_in_with_an_authenticator_code_confirms(client, authenticator):
    sign_in(client)
    enter_code(client, authenticator_code(authenticator.bin_key))

    assert client.get(SECURITY).status_code == 200


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_signing_in_with_a_recovery_code_confirms(client, owner):
    add_recovery_code(owner)
    sign_in(client)
    enter_code(client, "k7m2x9qa")

    assert client.get(SECURITY).status_code == 200


@pytest.mark.django_db
@pytest.mark.usefixtures("browser")
def test_signing_in_with_a_passkey_confirms(client, owner):
    add_passkey(owner)
    sign_in_with_passkey(client)

    assert client.get(SECURITY).status_code == 200


@pytest.mark.django_db
def test_claiming_with_an_authenticator_app_confirms(client):
    claim(client)
    set_up_authenticator(client)

    assert client.get(SECURITY).status_code == 200


@pytest.mark.django_db
@pytest.mark.usefixtures("browser")
def test_claiming_with_a_passkey_confirms(client):
    claim(client)
    register_passkey(client)

    assert client.get(SECURITY).status_code == 200
