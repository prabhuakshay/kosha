import pytest
from django.urls import reverse

from apps.core.testing import sub_links, tags
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
PAGES = ["base_currency", "history", "security", "sessions", "security_log"]


@pytest.mark.django_db
@pytest.mark.parametrize("name", PAGES)
def test_the_rail_and_tab_bar_are_current_anywhere_in_settings(signed_in, name):
    index = signed_in.get(SETTINGS)
    page = signed_in.get(reverse(name))

    assert tags(index, "a", href=SETTINGS, **{"aria-current": "page"})
    assert (
        tags(page, "a", href=SETTINGS, **{"class": "rail-link rail-wide"})[0][
            "aria-current"
        ]
        == "true"
    )
    assert tags(page, "a", href=SETTINGS, **{"class": "tab", "aria-current": "page"})


@pytest.mark.django_db
def test_the_wide_rail_shows_settings_pages_only_while_in_settings(signed_in):
    inside = signed_in.get(reverse("sessions"))
    outside = signed_in.get(reverse("home"))

    assert sub_links(inside, 'class="rail-sub"') == [reverse(n) for n in PAGES]
    assert 'class="rail-sub"' not in outside.text


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["home", "sessions"])
def test_the_icon_rail_opens_settings_in_a_flyout(signed_in, name):
    response = signed_in.get(reverse(name))

    assert tags(response, "button", popovertarget="settings-flyout")
    assert "popover" in tags(response, "div", id="settings-flyout")[0]
    assert sub_links(response, 'id="settings-flyout"') == [reverse(n) for n in PAGES]


def selected(response):
    current = tags(response, "a", **{"class": "sub-link", "aria-current": "page"})
    return {c["href"] for c in current}


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("name", "current"),
    [
        ("home", set()),
        ("settings", set()),
        ("base_currency", {reverse("base_currency")}),
        ("history", {reverse("history")}),
        ("security", {SECURITY}),
        ("password", {SECURITY}),
        ("sessions", {reverse("sessions")}),
        ("security_log", {reverse("security_log")}),
    ],
)
def test_the_settings_page_open_is_marked_current(signed_in, name, current):
    assert selected(signed_in.get(reverse(name))) == current


@pytest.mark.django_db
def test_confirm_marks_no_settings_page_current(signed_in, clock):
    clock.advance(minutes=11)

    assert selected(signed_in.get(reverse("confirm"))) == set()


def rows(response):
    return [r["href"] for r in tags(response, "a", **{"class": "row"})]


@pytest.mark.django_db
def test_the_settings_index_lists_every_page(signed_in):
    assert rows(signed_in.get(SETTINGS)) == [reverse(n) for n in PAGES]


@pytest.mark.django_db
@pytest.mark.parametrize("name", [*PAGES, "password"])
def test_a_settings_page_has_the_whole_pane_to_itself(signed_in, name):
    response = signed_in.get(reverse(name))

    assert rows(response) == []
    assert 'class="split' not in response.text


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
