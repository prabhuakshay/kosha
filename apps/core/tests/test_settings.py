import re

import pytest
from django.urls import reverse

from apps.core.testing import tags


def links(response, name):
    return tags(response, "a", href=reverse(name))


@pytest.mark.django_db
def test_the_owner_menu_leads_to_settings(signed_in):
    response = signed_in.get(reverse("home"))

    assert links(response, "settings")
    assert not links(response, "security")


@pytest.mark.django_db
def test_settings_leads_to_security_without_a_confirmation(signed_in, clock):
    clock.advance(minutes=11)

    response = signed_in.get(reverse("settings"))

    assert response.status_code == 200
    assert links(response, "security")


@pytest.mark.django_db
def test_settings_needs_signing_in(client):
    response = client.get(reverse("settings"))

    assert response["Location"].startswith(reverse("sign_in"))


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["security", "confirm"])
def test_security_goes_back_to_settings(signed_in, clock, name):
    if name == "confirm":
        clock.advance(minutes=11)

    response = signed_in.get(reverse(name))

    assert tags(
        response, "a", href=reverse("settings"), **{"aria-label": "Back to Settings"}
    )


@pytest.mark.django_db
def test_the_sidebar_leads_to_settings(signed_in):
    response = signed_in.get(reverse("settings"))

    assert tags(response, "a", href=reverse("settings"), **{"aria-current": "page"})


def breadcrumbs(response):
    nav = re.search(r'<nav aria-label="Breadcrumb".*?</nav>', response.text, re.DOTALL)
    return nav and re.findall(r'href="([^"]+)"', nav[0])


SETTINGS, SECURITY = reverse("settings"), reverse("security")


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("name", "trail"),
    [
        ("home", None),
        ("settings", None),
        ("security", [SETTINGS]),
        ("password", [SETTINGS, SECURITY]),
        ("sessions", [SETTINGS, SECURITY]),
        ("security_log", [SETTINGS, SECURITY]),
    ],
)
def test_pages_inside_settings_show_the_way_back_up(signed_in, name, trail):
    assert breadcrumbs(signed_in.get(reverse(name))) == trail


@pytest.mark.django_db
def test_confirm_shows_the_way_back_to_settings(signed_in, clock):
    clock.advance(minutes=11)

    assert breadcrumbs(signed_in.get(reverse("confirm"))) == [SETTINGS]


@pytest.mark.django_db
def test_new_recovery_codes_show_the_way_back_up(signed_in):
    response = signed_in.post(reverse("make_recovery_codes"), follow=True)

    assert breadcrumbs(response) == [SETTINGS, SECURITY]
