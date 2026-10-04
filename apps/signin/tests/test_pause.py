from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest
from axes.models import AccessAttempt
from django.db.models import F
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.core.testing import EMAIL
from apps.signin.models import SecurityLogEntry
from apps.signin.testing import (
    add_passkey,
    authenticator_code,
    enter_code,
    sign_in,
    sign_in_with_passkey,
)

WRONG_CODE = "000000"


def fail_password(client, times):
    for _ in range(times):
        sign_in(client, password="not it")


def forwarded_for(addresses):
    return Client(HTTP_X_FORWARDED_FOR=addresses)


def move_attempts_back(**delta):
    AccessAttempt.objects.update(attempt_time=F("attempt_time") - timedelta(**delta))


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_five_wrong_passwords_pause_signing_in(client):
    fail_password(client, 4)

    response = sign_in(client, password="not it")

    assert response.status_code == 429
    assert "Too many tries" in response.text
    assert "paused for an hour after 5 wrong passwords or codes" in response.text
    assert sign_in(client).status_code == 429
    assert client.get(reverse("home"))["Location"].startswith(reverse("sign_in"))


@pytest.mark.django_db
@pytest.mark.usefixtures("owner")
def test_the_paused_page_shows_instead_of_sign_in(client):
    fail_password(client, 5)

    response = client.get(reverse("sign_in"))

    assert response.status_code == 429
    assert "Too many tries" in response.text


@pytest.mark.django_db
@pytest.mark.usefixtures("owner")
def test_the_paused_page_says_when_to_try_again(client, settings):
    settings.TIME_ZONE = "Asia/Kolkata"
    fail_password(client, 5)
    # Axes reads the real clock, so the attempt is set just before it.
    attempt = timezone.now().replace(second=0, microsecond=0) - timedelta(minutes=1)
    AccessAttempt.objects.update(attempt_time=attempt)
    again = timezone.localtime(attempt + timedelta(hours=1), ZoneInfo("Asia/Kolkata"))

    response = client.get(reverse("sign_in"))

    half = "am" if again.hour < 12 else "pm"
    assert f"Try again after {again:%-I:%M} {half}" in response.text


@pytest.mark.django_db
def test_wrong_codes_pause_the_code_step(client, authenticator):
    sign_in(client)
    for _ in range(4):
        assert enter_code(client, WRONG_CODE).status_code == 200

    assert enter_code(client, WRONG_CODE).status_code == 429
    assert client.get(reverse("code_step")).status_code == 429
    code = authenticator_code(authenticator.bin_key)
    assert enter_code(client, code).status_code == 429
    assert client.get(reverse("home"))["Location"].startswith(reverse("code_step"))


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_wrong_recovery_codes_count(client):
    sign_in(client)
    for _ in range(4):
        enter_code(client, "abcd efgh")

    assert enter_code(client, "abcd efgh").status_code == 429


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_a_right_password_does_not_reset_the_count(client):
    fail_password(client, 3)
    sign_in(client)

    assert enter_code(client, WRONG_CODE).status_code == 200
    assert enter_code(client, WRONG_CODE).status_code == 429


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_the_pause_lifts_after_an_hour(client):
    fail_password(client, 5)

    move_attempts_back(hours=1, minutes=1)

    assert sign_in(client)["Location"] == reverse("home")


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_tries_during_the_pause_do_not_extend_it(client):
    fail_password(client, 5)
    move_attempts_back(minutes=50)

    fail_password(client, 3)
    move_attempts_back(minutes=11)

    assert sign_in(client)["Location"] == reverse("home")


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_only_the_address_is_paused(client):
    fail_password(client, 5)

    elsewhere = Client(REMOTE_ADDR="203.0.113.9")

    assert sign_in(elsewhere)["Location"] == reverse("home")


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_a_pause_is_logged_once(client):
    fail_password(client, 5)

    fail_password(client, 3)
    client.get(reverse("sign_in"))

    paused = SecurityLogEntry.objects.filter(kind=SecurityLogEntry.Kind.PAUSED)
    assert paused.count() == 1


@pytest.mark.django_db
@pytest.mark.usefixtures("browser")
def test_a_passkey_cannot_sign_in_from_a_paused_address(client, owner):
    add_passkey(owner)
    fail_password(client, 5)

    assert sign_in_with_passkey(client).status_code == 429
    assert client.get(reverse("home"))["Location"].startswith(reverse("sign_in"))


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_the_forwarded_address_is_ignored_unless_behind_a_proxy():
    fail_password(forwarded_for("198.51.100.7"), 5)

    assert sign_in(forwarded_for("203.0.113.9")).status_code == 429


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_behind_a_proxy_the_forwarded_address_is_paused(settings):
    settings.USE_X_FORWARDED_FOR = True
    fail_password(forwarded_for("198.51.100.7"), 5)

    assert sign_in(forwarded_for("198.51.100.7")).status_code == 429
    assert sign_in(forwarded_for("203.0.113.9"))["Location"] == reverse("home")


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_behind_a_proxy_a_spoofed_address_does_not_escape_the_pause(settings):
    settings.USE_X_FORWARDED_FOR = True
    fail_password(forwarded_for("198.51.100.7"), 5)

    response = sign_in(forwarded_for("203.0.113.9, 198.51.100.7"))

    assert response.status_code == 429


@pytest.mark.django_db
@pytest.mark.usefixtures("owner")
def test_wrong_tries_are_counted_against_the_address_not_the_email(client):
    fail_password(client, 3)
    sign_in(client, email="someone@example.com", password="not it")

    response = sign_in(client, email=EMAIL.upper(), password="not it")

    assert response.status_code == 429


@pytest.mark.django_db
@pytest.mark.usefixtures("owner")
def test_the_pause_lasts_an_hour_from_when_it_began(client):
    fail_password(Client(HTTP_USER_AGENT="Firefox/143.0"), 4)
    move_attempts_back(minutes=50)
    fail_password(client, 1)

    move_attempts_back(minutes=15)

    assert client.get(reverse("sign_in")).status_code == 429
