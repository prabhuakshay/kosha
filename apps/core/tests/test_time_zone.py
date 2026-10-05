import re
from datetime import UTC, datetime

import pytest
from django.urls import reverse

from apps.core.testing import chosen
from apps.core.testing import shown_history as shown
from apps.signin.testing import (
    authenticator_code,
    claim,
    enter_code,
    set_up_authenticator,
)

TIME_ZONE = reverse("time_zone")


def stamps(response):
    return re.findall(r'class="stamp">([^<]+)<', response.text)


pytestmark = pytest.mark.usefixtures("server_in_utc")


@pytest.fixture
def at_half_past_three_utc(time_machine):
    time_machine.move_to(datetime(2026, 10, 12, 3, 30, tzinfo=UTC), tick=False)


@pytest.mark.django_db
def test_the_servers_time_zone_is_used_until_one_is_set(signed_in):
    assert chosen(signed_in.get(TIME_ZONE)) == ["UTC"]


@pytest.mark.django_db
def test_the_owner_changes_it(signed_in):
    response = signed_in.post(TIME_ZONE, {"time_zone": "Asia/Kolkata"}, follow=True)

    assert chosen(response) == ["Asia/Kolkata"]
    assert "Today is now worked out in Asia/Kolkata." in response.text


@pytest.mark.django_db
def test_settings_lists_it(signed_in):
    signed_in.post(TIME_ZONE, {"time_zone": "Asia/Kolkata"})

    response = signed_in.get(reverse("settings"))

    assert re.search(r"Time zone</span>.*?Asia/Kolkata", response.text, re.DOTALL)


@pytest.mark.django_db
def test_an_unknown_time_zone_is_refused(signed_in):
    response = signed_in.post(TIME_ZONE, {"time_zone": "Mars/Olympus_Mons"})

    assert response.status_code == 200
    assert chosen(signed_in.get(TIME_ZONE)) == ["UTC"]


@pytest.mark.django_db
def test_changing_it_is_in_history(signed_in):
    signed_in.post(TIME_ZONE, {"time_zone": "Asia/Kolkata"})
    signed_in.post(TIME_ZONE, {"time_zone": "Europe/London"})

    assert shown(signed_in.get(reverse("history"))) == [
        (
            "Time zone changed Time zone · Setting Time zone: Asia/Kolkata → "
            "Europe/London"
        ),
        "Time zone changed Time zone · Setting Time zone: UTC → Asia/Kolkata",
    ]


@pytest.mark.django_db
def test_keeping_it_adds_nothing_to_history(signed_in):
    signed_in.post(TIME_ZONE, {"time_zone": "UTC"})

    assert shown(signed_in.get(reverse("history"))) == []


@pytest.mark.django_db
def test_claiming_sets_it_from_the_browser(client):
    client.cookies["time_zone"] = "Asia/Kolkata"
    claim(client)
    set_up_authenticator(client)

    assert chosen(client.get(TIME_ZONE)) == ["Asia/Kolkata"]


@pytest.mark.django_db
def test_an_existing_install_takes_it_from_the_browser_once(signed_in):
    signed_in.cookies["time_zone"] = "Asia/Kolkata"
    signed_in.get(reverse("home"))
    signed_in.cookies["time_zone"] = "Europe/London"
    signed_in.get(reverse("home"))

    assert chosen(signed_in.get(TIME_ZONE)) == ["Asia/Kolkata"]
    assert shown(signed_in.get(reverse("history"))) == []


@pytest.mark.django_db
def test_the_browser_doesnt_override_a_time_zone_the_owner_chose(signed_in):
    signed_in.post(TIME_ZONE, {"time_zone": "Europe/London"})
    signed_in.cookies["time_zone"] = "Asia/Kolkata"
    signed_in.get(reverse("home"))

    assert chosen(signed_in.get(TIME_ZONE)) == ["Europe/London"]


@pytest.mark.django_db
def test_a_time_zone_the_browser_makes_up_is_ignored(signed_in):
    signed_in.cookies["time_zone"] = "Mars/Olympus_Mons"
    signed_in.get(reverse("home"))

    assert chosen(signed_in.get(TIME_ZONE)) == ["UTC"]


@pytest.mark.django_db
def test_a_password_alone_doesnt_set_it(client, owner, authenticator):
    client.force_login(owner)
    client.cookies["time_zone"] = "Asia/Kolkata"
    client.get(reverse("home"))
    del client.cookies["time_zone"]
    enter_code(client, authenticator_code(authenticator.bin_key))

    assert chosen(client.get(TIME_ZONE)) == ["UTC"]


@pytest.mark.django_db
def test_the_security_log_is_in_the_owners_time_zone(at_half_past_three_utc, signed_in):
    signed_in.post(TIME_ZONE, {"time_zone": "Asia/Kolkata"})

    response = signed_in.get(reverse("security_log"))

    assert stamps(response) == ["9:00 am"]


@pytest.mark.django_db
def test_history_is_in_the_owners_time_zone(at_half_past_three_utc, signed_in):
    signed_in.post(TIME_ZONE, {"time_zone": "Asia/Kolkata"})

    response = signed_in.get(reverse("history"))

    assert stamps(response) == ["9:00 am"]


@pytest.mark.django_db
def test_it_needs_signing_in(client):
    response = client.get(TIME_ZONE)

    assert response["Location"].startswith(reverse("sign_in"))
