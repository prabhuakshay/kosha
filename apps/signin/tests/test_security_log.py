import re
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils.timezone import localdate
from django_otp.plugins.otp_static.models import StaticDevice

from apps.signin.models import SecurityLogEntry
from apps.signin.testing import (
    CHROME_ON_MAC,
    add_passkey,
    authenticator_code,
    claim,
    enter_code,
    set_up_authenticator,
    sign_in,
    sign_in_with_passkey,
)

Kind = SecurityLogEntry.Kind
pytestmark = pytest.mark.usefixtures("from_a_mac")


@pytest.fixture
def from_a_mac(client):
    client.defaults.update(HTTP_USER_AGENT=CHROME_ON_MAC, REMOTE_ADDR="198.51.100.7")


def logged():
    return [(entry.kind, entry.detail) for entry in SecurityLogEntry.objects.all()]


@pytest.mark.django_db
def test_signing_in_with_password_and_code_is_logged(client, authenticator):
    sign_in(client)
    assert logged() == []

    enter_code(client, authenticator_code(authenticator.bin_key))

    entry = SecurityLogEntry.objects.get()
    assert (entry.kind, entry.detail) == (
        Kind.SIGNED_IN,
        "Password and authenticator code",
    )
    assert entry.address == "198.51.100.7"
    assert entry.device == "Chrome on macOS"


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_signing_in_with_a_recovery_code_is_logged(client, owner):
    device = StaticDevice.objects.create(user=owner, name="Recovery codes")
    device.token_set.create(token="k7m2x9qa")
    sign_in(client)

    enter_code(client, "k7m2 x9qa")

    assert logged() == [(Kind.SIGNED_IN, "Password and recovery code")]


@pytest.mark.django_db
@pytest.mark.usefixtures("browser")
def test_signing_in_with_a_passkey_is_logged(client, owner):
    add_passkey(owner)

    sign_in_with_passkey(client)

    assert logged() == [(Kind.SIGNED_IN, "Passkey")]


@pytest.mark.django_db
@pytest.mark.usefixtures("browser", "authenticator")
def test_a_passkey_at_the_code_step_is_logged(client, owner):
    add_passkey(owner)
    sign_in(client)

    sign_in_with_passkey(client)

    assert logged() == [(Kind.SIGNED_IN, "Password and passkey")]


@pytest.mark.django_db
def test_claim_logs_signing_in_with_the_password(client):
    claim(client)

    assert logged() == [(Kind.SIGNED_IN, "Password")]


@pytest.mark.django_db
def test_recovery_codes_are_logged_once_at_claim(client):
    claim(client)
    set_up_authenticator(client)

    client.get(reverse("recovery_codes"))
    client.get(reverse("recovery_codes"))

    assert logged() == [
        (Kind.RECOVERY_CODES_ISSUED, ""),
        (Kind.AUTHENTICATOR_SET_UP, ""),
        (Kind.SIGNED_IN, "Password"),
    ]
    entry = SecurityLogEntry.objects.first()
    assert (entry.address, entry.device) == ("198.51.100.7", "Chrome on macOS")


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_recovery_codes_after_a_server_reset_are_logged(client):
    call_command("break_glass", "--ways-to-sign-in", stdout=StringIO())
    sign_in(client)
    set_up_authenticator(client)

    response = client.get(reverse("recovery_codes"))

    assert response.status_code == 200
    assert logged() == [
        (Kind.RECOVERY_CODES_ISSUED, ""),
        (Kind.AUTHENTICATOR_SET_UP, ""),
        (Kind.SIGNED_IN, "Password"),
        (Kind.RESET_ON_SERVER, "Ways to sign in"),
    ]


@pytest.mark.django_db
@pytest.mark.usefixtures("owner")
def test_signing_in_with_no_way_to_sign_in_is_logged(client):
    sign_in(client)

    assert logged() == [(Kind.SIGNED_IN, "Password")]


@pytest.mark.django_db
@pytest.mark.usefixtures("owner")
def test_a_wrong_password_is_logged(client):
    sign_in(client, password="not it")

    assert logged() == [(Kind.WRONG_PASSWORD, "")]


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_a_wrong_code_is_logged(client):
    sign_in(client)

    enter_code(client, "000000")

    assert logged() == [(Kind.WRONG_CODE, "")]


@pytest.mark.django_db
def test_the_log_is_newest_first(client, authenticator):
    sign_in(client, password="not it")
    sign_in(client)
    enter_code(client, "abcd efgh")
    enter_code(client, authenticator_code(authenticator.bin_key))

    assert [kind for kind, _ in logged()] == [
        Kind.SIGNED_IN,
        Kind.WRONG_CODE,
        Kind.WRONG_PASSWORD,
    ]


@pytest.mark.django_db
@pytest.mark.usefixtures("owner")
def test_the_pause_is_logged_after_the_wrong_tries_that_caused_it(client):
    for _ in range(5):
        sign_in(client, password="not it")

    assert [kind for kind, _ in logged()] == [Kind.PAUSED] + [Kind.WRONG_PASSWORD] * 4


@pytest.mark.django_db
@pytest.mark.usefixtures("owner")
@pytest.mark.parametrize(
    ("user_agent", "device"),
    [
        (
            (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 "
                "Mobile/15E148 Safari/604.1"
            ),
            "Safari on iPhone",
        ),
        (
            (
                "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36"
            ),
            "Chrome on Android",
        ),
        (
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) "
                "Gecko/20100101 Firefox/143.0"
            ),
            "Firefox on Windows",
        ),
        (
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0"
            ),
            "Edge on Windows",
        ),
        ("", "Unknown device"),
    ],
)
def test_the_device_is_named_without_versions(client, user_agent, device):
    client.defaults["HTTP_USER_AGENT"] = user_agent

    sign_in(client, password="not it")

    assert SecurityLogEntry.objects.get().device == device


@pytest.mark.django_db
def test_the_admin_shows_the_log_read_only(signed_in):
    entry = SecurityLogEntry.objects.get()
    changelist = reverse("admin:signin_securitylogentry_changelist")

    assert "Signed in" in signed_in.get(changelist).text
    add = reverse("admin:signin_securitylogentry_add")
    assert signed_in.get(add).status_code == 403
    change = reverse("admin:signin_securitylogentry_change", args=[entry.pk])
    assert signed_in.post(change, {"detail": "edited"}).status_code == 403
    delete = reverse("admin:signin_securitylogentry_delete", args=[entry.pk])
    assert signed_in.post(delete, {"post": "yes"}).status_code == 403
    signed_in.post(
        changelist, {"action": "delete_selected", "_selected_action": [entry.pk]}
    )
    assert logged() == [(Kind.SIGNED_IN, "Password and authenticator code")]


def shown_entries(response):
    return re.findall(r"data-log-kind>([^<]+)<", response.text)


@pytest.mark.django_db
def test_the_log_screen_lists_entries_newest_first(client, authenticator):
    sign_in(client, password="not it")
    sign_in(client)
    enter_code(client, authenticator_code(authenticator.bin_key))

    response = client.get(reverse("security_log"))

    assert shown_entries(response) == ["Signed in", "Wrong email or password"]
    assert "Password and authenticator code" in response.text
    assert "Chrome on macOS · 198.51.100.7" in response.text


@pytest.mark.django_db
def test_the_log_screen_shows_what_happened_on_the_server(client, owner, authenticator):
    call_command("break_glass", "--password", stdout=StringIO())
    owner.refresh_from_db()
    client.force_login(owner)
    enter_code(client, authenticator_code(authenticator.bin_key))

    response = client.get(reverse("security_log"))

    assert shown_entries(response) == ["Signed in", "Reset on the server"]
    assert "On the server" in response.text


@pytest.mark.django_db
def test_the_log_screen_groups_entries_by_day(signed_in, clock):
    for days_ago in (1, 3):
        SecurityLogEntry.objects.create(
            kind=Kind.WRONG_PASSWORD, at=clock.now - timedelta(days=days_ago)
        )

    response = signed_in.get(reverse("security_log"))

    earlier = localdate(clock.now - timedelta(days=3))
    assert re.findall(r"data-log-day>([^<]+)<", response.text) == [
        "Today",
        "Yesterday",
        f"{earlier:%-d %b %Y}",
    ]
