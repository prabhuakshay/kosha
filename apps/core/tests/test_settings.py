import pytest
from django.urls import reverse

from apps.core.testing import tags
from apps.signin.testing import add_passkey


def links(response, name):
    return tags(response, "a", href=reverse(name))


@pytest.mark.django_db
def test_every_page_leads_to_settings(signed_in):
    response = signed_in.get(reverse("home"))

    assert links(response, "settings")


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


SETTINGS, SECURITY = reverse("settings"), reverse("security")
PAGES = [
    "base_currency",
    "time_zone",
    "history",
    "appearance",
    "security",
    "sessions",
    "security_log",
]


LISTS = [reverse(f"masters:{n}") for n in ["accounts", "categories", "tags"]]


@pytest.mark.django_db
@pytest.mark.parametrize("name", PAGES)
def test_the_side_bar_and_tab_bar_are_current_anywhere_in_settings(signed_in, name):
    index = signed_in.get(SETTINGS)
    page = signed_in.get(reverse(name))

    assert tags(
        index, "a", href=SETTINGS, **{"class": "side-link", "aria-current": "page"}
    )
    assert tags(
        page, "a", href=SETTINGS, **{"class": "side-link", "aria-current": "true"}
    )
    assert tags(page, "a", href=SETTINGS, **{"class": "tab", "aria-current": "page"})


def selected(response):
    current = tags(response, "a", **{"class": "row", "aria-current": "page"})
    return {c["href"] for c in current}


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("name", "current"),
    [
        ("home", set()),
        ("settings", set()),
        ("base_currency", {reverse("base_currency")}),
        ("time_zone", {reverse("time_zone")}),
        ("history", {reverse("history")}),
        ("appearance", {reverse("appearance")}),
        ("security", {SECURITY}),
        ("password", {SECURITY}),
        ("sessions", {reverse("sessions")}),
        ("security_log", {reverse("security_log")}),
    ],
)
def test_the_settings_page_open_is_marked_current(signed_in, name, current):
    assert selected(signed_in.get(reverse(name))) == current


@pytest.mark.django_db
def test_confirm_counts_as_signing_in(signed_in, clock):
    clock.advance(minutes=11)

    assert selected(signed_in.get(reverse("confirm"))) == {SECURITY}


def rows(response):
    return [r["href"] for r in tags(response, "a", **{"class": "row"})]


@pytest.mark.django_db
def test_the_settings_index_lists_every_page(signed_in):
    assert rows(signed_in.get(SETTINGS))[:10] == LISTS + [reverse(n) for n in PAGES]


@pytest.mark.django_db
@pytest.mark.parametrize("name", [*PAGES, "password"])
def test_a_settings_page_sits_beside_the_settings_list(signed_in, name):
    response = signed_in.get(reverse(name))

    assert rows(response)[:10] == LISTS + [reverse(n) for n in PAGES]
    assert 'class="split split-open"' in response.text


@pytest.mark.django_db
def test_new_recovery_codes_go_back_to_signing_in(signed_in):
    response = signed_in.post(reverse("make_recovery_codes"), follow=True)

    assert selected(response) == {SECURITY}
    assert tags(
        response,
        "a",
        href=SECURITY,
        **{"aria-label": "Back to Signing in"},
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name", ["password", "new_recovery_codes", "new_authenticator"]
)
def test_pages_under_signing_in_always_show_the_way_back_up(signed_in, name):
    if name == "new_recovery_codes":
        response = signed_in.post(reverse("make_recovery_codes"), follow=True)
    elif name == "new_authenticator":
        response = signed_in.post(reverse("start_authenticator"), follow=True)
    else:
        response = signed_in.get(reverse(name))

    assert tags(
        response,
        "a",
        href=SECURITY,
        **{"class": "back", "aria-label": "Back to Signing in"},
    )


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
