import pytest
from django.urls import reverse

from apps.core.testing import tags
from apps.signin.testing import add_passkey


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


def selected(response):
    rows = tags(response, "a", **{"class": "row"})
    return rows and [r["href"] for r in rows if r.get("aria-current") == "page"]


SETTINGS, SECURITY = reverse("settings"), reverse("security")


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("name", "rows"),
    [
        ("home", []),
        ("settings", []),
        ("security", [SECURITY]),
        ("password", [SECURITY]),
        ("sessions", [reverse("sessions")]),
        ("security_log", [reverse("security_log")]),
    ],
)
def test_pages_inside_settings_sit_beside_its_list(signed_in, name, rows):
    response = signed_in.get(reverse(name))

    assert selected(response) == rows
    if name != "home":
        assert links(response, "security_log")


@pytest.mark.django_db
def test_confirm_sits_beside_the_settings_list(signed_in, clock):
    clock.advance(minutes=11)

    assert selected(signed_in.get(reverse("confirm"))) == []


@pytest.mark.django_db
def test_new_recovery_codes_go_back_to_signing_in(signed_in):
    response = signed_in.post(reverse("make_recovery_codes"), follow=True)

    assert selected(response) == [SECURITY]
    assert tags(
        response,
        "a",
        href=SECURITY,
        **{"aria-label": "Back to Signing in"},
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("name", "here"),
    [
        ("password", "Password"),
        ("new_recovery_codes", "New recovery codes"),
        ("new_authenticator", "Authenticator app"),
    ],
)
def test_pages_under_signing_in_show_the_way_back_up(signed_in, name, here):
    if name == "new_recovery_codes":
        response = signed_in.post(reverse("make_recovery_codes"), follow=True)
    elif name == "new_authenticator":
        response = signed_in.post(reverse("start_authenticator"), follow=True)
    else:
        response = signed_in.get(reverse(name))

    assert tags(response, "nav", **{"aria-label": "Breadcrumb"})
    assert links(response, "settings")
    assert links(response, "security")
    assert f'<li aria-current="page">{here}</li>' in response.text


def asks_first(response, sheet, action):
    """The form posting to `action` is only in a sheet a button opens."""
    return (
        tags(response, "button", type="button", popovertarget=sheet)
        and "popover" in tags(response, "div", id=sheet)[0]
        and len(tags(response, "form", action=action)) == 1
    )


@pytest.mark.django_db
def test_destructive_changes_to_signing_in_ask_first(signed_in, owner):
    passkey = add_passkey(owner)

    response = signed_in.get(SECURITY)

    assert asks_first(
        response,
        f"remove-passkey-{passkey.pk}",
        reverse("remove_passkey", args=[passkey.pk]),
    )
    assert asks_first(response, "remove-authenticator", reverse("remove_authenticator"))
    assert asks_first(response, "make-recovery-codes", reverse("make_recovery_codes"))
