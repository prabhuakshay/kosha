import re

import pytest
from django.urls import reverse
from django.utils.timezone import localtime

from apps.core.testing import tags
from apps.signin.models import SecurityLogEntry
from apps.signin.testing import (
    FIREFOX_ON_WINDOWS,
    SAFARI_ON_IPHONE,
    browser_at,
    sign_in,
    sign_in_fully,
)

Kind = SecurityLogEntry.Kind
SESSIONS = reverse("sessions")
SIGN_OUT_OTHERS = reverse("sign_out_others")


@pytest.mark.django_db
def test_sessions_shows_this_one(authenticator, clock):
    iphone = browser_at("203.0.113.5", SAFARI_ON_IPHONE)
    sign_in_fully(iphone, authenticator)
    clock.advance(minutes=5)

    response = iphone.get(SESSIONS)

    assert "Safari on iPhone" in response.text
    assert "203.0.113.5" in response.text
    assert f"Signed in {localtime(clock.now):%-d %b %Y}" in response.text
    assert active(clock.now) in response.text
    assert "This device" in response.text


def active(at):
    at = localtime(at)
    return f"Active {at:%-d %b %Y}, {f'{at:%-I:%M %p}'.lower()}"


def listed_devices(response):
    return re.findall(r"data-session-device>([^<]+)<", response.text)


@pytest.mark.django_db
def test_sessions_lists_every_session_this_one_first(authenticator, clock):
    windows = browser_at("198.51.100.9", FIREFOX_ON_WINDOWS)
    sign_in_fully(windows, authenticator)
    clock.advance(hours=1)
    iphone = browser_at("203.0.113.5", SAFARI_ON_IPHONE)
    sign_in_fully(iphone, authenticator, 1)
    clock.advance(minutes=5)
    windows.get(reverse("home"))

    response = iphone.get(SESSIONS)

    assert listed_devices(response) == ["Safari on iPhone", "Firefox on Windows"]
    assert response.text.count("This device") == 1
    assert "198.51.100.9" in response.text
    assert active(clock.now) in response.text


@pytest.mark.django_db
def test_a_session_that_only_passed_the_password_is_marked(authenticator):
    sign_in(browser_at("198.51.100.9", FIREFOX_ON_WINDOWS))
    iphone = browser_at("203.0.113.5", SAFARI_ON_IPHONE)
    sign_in_fully(iphone, authenticator)

    response = iphone.get(SESSIONS)

    assert response.text.count("Password only") == 1
    assert listed_devices(response) == ["Safari on iPhone", "Firefox on Windows"]


@pytest.mark.django_db
def test_sign_out_everywhere_else(authenticator):
    windows = browser_at("198.51.100.9", FIREFOX_ON_WINDOWS)
    sign_in_fully(windows, authenticator)
    iphone = browser_at("203.0.113.5", SAFARI_ON_IPHONE)
    sign_in_fully(iphone, authenticator, 1)

    response = iphone.post(SIGN_OUT_OTHERS, follow=True)

    assert listed_devices(response) == ["Safari on iPhone"]
    assert "Signed out everywhere else." in response.text
    assert windows.get(reverse("home"))["Location"].startswith(reverse("sign_in"))
    assert iphone.get(reverse("home")).status_code == 200
    entry = SecurityLogEntry.objects.first()
    assert (entry.kind, entry.device) == (Kind.SIGNED_OUT_ELSEWHERE, "Safari on iPhone")


@pytest.mark.django_db
def test_signing_out_everywhere_else_needs_a_confirmation(signed_in, clock):
    clock.advance(minutes=11)

    response = signed_in.post(SIGN_OUT_OTHERS)

    assert response["Location"].startswith(reverse("confirm"))
    assert not SecurityLogEntry.objects.filter(kind=Kind.SIGNED_OUT_ELSEWHERE)


@pytest.mark.django_db
def test_signing_out_everywhere_else_is_offered_only_with_others(signed_in):
    response = signed_in.get(SESSIONS)

    assert not tags(response, "form", action=SIGN_OUT_OTHERS)


@pytest.mark.django_db
def test_signing_out_everywhere_else_asks_first(authenticator):
    windows = browser_at("198.51.100.9", FIREFOX_ON_WINDOWS)
    sign_in_fully(windows, authenticator)
    iphone = browser_at("203.0.113.5", SAFARI_ON_IPHONE)
    sign_in_fully(iphone, authenticator, 1)

    response = iphone.get(SESSIONS)

    assert tags(response, "button", type="button", popovertarget="sign-out-others")
    assert "popover" in tags(response, "div", id="sign-out-others")[0]
    assert tags(response, "form", action=SIGN_OUT_OTHERS)
