import re

import pytest
from django.urls import reverse
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.core.testing import tags
from apps.signin.testing import (
    claim,
    set_up_authenticator,
    shown_codes,
    shown_key,
)


@pytest.mark.django_db
def test_claim_continues_to_choosing_a_way_to_sign_in(client):
    response = claim(client)

    assert response["Location"] == reverse("choose_way")
    response = client.get(reverse("choose_way"))
    assert "Choose a way to sign in" in response.text
    assert reverse("set_up_authenticator") in response.text


@pytest.mark.django_db
def test_authenticator_setup_shows_a_qr_code_and_the_key_in_groups_of_four(client):
    claim(client)

    response = client.get(reverse("set_up_authenticator"))

    assert tags(response, "svg")
    assert re.fullmatch(r"([A-Z2-7]{4} ){7}[A-Z2-7]{4}", shown_key(response))


@pytest.mark.django_db
def test_authenticator_key_stays_the_same_across_reloads(client):
    claim(client)

    first = shown_key(client.get(reverse("set_up_authenticator")))

    assert shown_key(client.get(reverse("set_up_authenticator"))) == first


@pytest.mark.django_db
def test_right_code_turns_the_authenticator_app_on(client):
    claim(client)

    response = set_up_authenticator(client)

    assert response["Location"] == reverse("recovery_codes")
    assert TOTPDevice.objects.get().config_url.endswith("issuer=Kosha")


@pytest.mark.django_db
def test_wrong_code_turns_nothing_on(client):
    claim(client)

    response = set_up_authenticator(client, "000000")

    assert response.status_code == 200
    assert "That code doesn&#x27;t match. Try the one showing now." in response.text
    assert not TOTPDevice.objects.exists()


@pytest.mark.django_db
def test_ten_recovery_codes_are_shown_once_then_home(client):
    claim(client)
    set_up_authenticator(client)

    response = client.get(reverse("recovery_codes"))

    assert len(set(shown_codes(response))) == 10
    assert tags(response, "a", href=reverse("home"))
    again = client.get(reverse("recovery_codes"))
    assert again["Location"] == reverse("home")
    assert client.get(reverse("home")).status_code == 200
