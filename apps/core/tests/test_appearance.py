import re

import pytest
from django.urls import reverse

from apps.core.testing import tags

APPEARANCE = reverse("appearance")


def theme(response):
    return tags(response, "html")[0].get("class")


def theme_colors(response):
    return [
        (m["content"], m.get("media"))
        for m in tags(response, "meta", name="theme-color")
    ]


def pressed(response):
    return [
        b["value"]
        for b in tags(response, "button", name="theme", **{"aria-pressed": "true"})
    ]


@pytest.mark.django_db
def test_a_new_device_follows_its_own_light_or_dark(signed_in):
    response = signed_in.get(APPEARANCE)

    assert pressed(response) == ["auto"]
    assert theme(response) is None
    assert theme_colors(response) == [
        ("#fafaf8", "(prefers-color-scheme: light)"),
        ("#1b1d1d", "(prefers-color-scheme: dark)"),
    ]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("choice", "color"), [("light", "#fafaf8"), ("dark", "#1b1d1d")]
)
def test_the_owner_chooses_light_or_dark_for_every_page(signed_in, choice, color):
    response = signed_in.post(APPEARANCE, {"theme": choice})

    assert response["Location"] == APPEARANCE
    for page in (signed_in.get(APPEARANCE), signed_in.get(reverse("home"))):
        assert theme(page) == choice
        assert theme_colors(page) == [(color, None)]
    assert pressed(signed_in.get(APPEARANCE)) == [choice]


@pytest.mark.django_db
def test_going_back_to_auto_follows_the_device_again(signed_in):
    signed_in.post(APPEARANCE, {"theme": "dark"})

    signed_in.post(APPEARANCE, {"theme": "auto"})

    response = signed_in.get(APPEARANCE)
    assert pressed(response) == ["auto"]
    assert theme(response) is None


@pytest.mark.django_db
def test_the_choice_lasts_beyond_a_session(signed_in):
    response = signed_in.post(APPEARANCE, {"theme": "dark"})

    cookie = response.cookies["theme"]
    assert cookie["max-age"] == 400 * 24 * 60 * 60
    assert cookie["httponly"]
    assert cookie["samesite"] == "Lax"


@pytest.mark.django_db
def test_the_choice_applies_on_the_sign_in_page_too(client, owner):
    client.cookies["theme"] = "dark"

    response = client.get(reverse("sign_in"))

    assert theme(response) == "dark"


@pytest.mark.django_db
@pytest.mark.parametrize("choice", ["sepia", ""])
def test_an_unknown_choice_changes_nothing(signed_in, choice):
    signed_in.post(APPEARANCE, {"theme": "dark"})

    signed_in.post(APPEARANCE, {"theme": choice})

    assert theme(signed_in.get(APPEARANCE)) == "dark"


@pytest.mark.django_db
def test_an_unknown_theme_cookie_is_auto(signed_in):
    signed_in.cookies["theme"] = "x onload=alert(1)"

    response = signed_in.get(APPEARANCE)

    assert pressed(response) == ["auto"]
    assert theme(response) is None


@pytest.mark.django_db
def test_choosing_reloads_the_whole_page(signed_in):
    # A swapped-in body would leave the <html> element's theme as it was.
    response = signed_in.get(APPEARANCE)

    assert tags(response, "form", method="post", **{"hx-boost": "false"})


@pytest.mark.django_db
def test_settings_says_how_this_browser_looks(signed_in):
    signed_in.post(APPEARANCE, {"theme": "light"})

    response = signed_in.get(reverse("settings"))

    subs = re.findall(
        r'font-semibold">([^<]+)</span>\s*<span class="row-sub">([^<]+)<',
        response.text,
    )
    assert ("Appearance", "Light") in subs
