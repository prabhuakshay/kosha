import re

import pytest
from django.urls import reverse

from apps.core.testing import tags
from apps.masters.models import Category
from apps.masters.testing import category, history, listed_at, notices
from apps.masters.testing import category_url as url

CATEGORIES = reverse("masters:categories")
NEW = reverse("masters:new_category")


@pytest.mark.django_db
def test_one_is_closed_into_the_collapsed_closed_section(signed_in):
    groceries = category()
    category("Rent")

    response = signed_in.post(url("close_", groceries), follow=True)

    groceries.refresh_from_db()
    assert groceries.closed
    assert notices(response) == ["Closed Groceries."]
    assert listed_at(signed_in, CATEGORIES) == (["Rent"], ["Groceries"])
    section = tags(signed_in.get(CATEGORIES), "details")
    assert len(section) == 1
    assert "open" not in section[0]


@pytest.mark.django_db
def test_the_closed_section_is_open_while_one_in_it_is(signed_in):
    groceries = category(closed=True)

    response = signed_in.get(url("", groceries))

    assert "open" in tags(response, "details")[0]
    assert "data-closed-badge" in response.text
    assert tags(response, "a", href=url("", groceries), **{"aria-current": "page"})


@pytest.mark.django_db
def test_a_list_of_only_closed_ones_isnt_empty(signed_in):
    category(closed=True)

    response = signed_in.get(CATEGORIES)

    assert "yet</h1>" not in response.text
    assert "None open" in response.text


@pytest.mark.django_db
def test_a_closed_one_is_reopened(signed_in):
    groceries = category(closed=True)

    response = signed_in.post(url("reopen_", groceries), follow=True)

    groceries.refresh_from_db()
    assert not groceries.closed
    assert notices(response) == ["Reopened Groceries."]
    assert listed_at(signed_in, CATEGORIES) == (["Groceries"], [])


@pytest.mark.django_db
def test_an_unused_one_is_deleted(signed_in):
    groceries = category()

    response = signed_in.post(url("delete_", groceries), follow=True)

    assert not Category.objects.exists()
    assert response.redirect_chain[-1][0] == CATEGORIES
    assert notices(response) == ["Deleted Groceries."]


@pytest.mark.django_db
def test_one_something_refers_to_cant_be_deleted(signed_in, monkeypatch):
    groceries = category()
    monkeypatch.setattr(Category, "in_use", property(lambda _: True))

    response = signed_in.post(url("delete_", groceries), follow=True)

    assert Category.objects.get() == groceries
    assert notices(response) == [
        "Groceries can't be deleted while anything refers to it. Close it instead."
    ]
    assert not tags(response, "form", action=url("delete_", groceries))


def sheet_for(response, action):
    """The confirm sheet a form posting to ``action`` sits in, by its id."""
    form = re.search(
        rf'<form [^>]*action="{action}".*?</form>', response.text, re.DOTALL
    )
    cancel = form and re.search(
        r'popovertarget="([\w-]+)" popovertargetaction="hide"[^>]*autofocus', form[0]
    )
    return cancel and cancel[1]


@pytest.mark.django_db
@pytest.mark.parametrize("action", ["close_", "delete_"])
def test_close_and_delete_ask_first(signed_in, action):
    groceries = category()

    response = signed_in.get(url("", groceries))

    sheet = sheet_for(response, url(action, groceries))
    assert "popover" in tags(response, "div", id=sheet)[0]
    assert tags(response, "button", popovertarget=sheet, type="button")


@pytest.mark.django_db
def test_reopen_doesnt_ask_first(signed_in):
    groceries = category(closed=True)

    response = signed_in.get(url("", groceries))

    assert tags(response, "form", method="post", action=url("reopen_", groceries))
    assert not sheet_for(response, url("reopen_", groceries))
    assert not tags(response, "form", action=url("close_", groceries))


@pytest.mark.django_db
def test_closing_reopening_and_deleting_are_in_history(signed_in):
    groceries = category()

    signed_in.post(url("close_", groceries))
    signed_in.post(url("reopen_", groceries))
    assert history(signed_in.get(url("", groceries))) == (["Reopened", "Closed"], [])

    signed_in.post(url("delete_", groceries))
    response = signed_in.get(reverse("history"))
    assert re.findall(r"data-history-action>([^<]+)<", response.text) == [
        "Deleted",
        "Reopened",
        "Closed",
    ]
    assert "data-history-subject>Groceries · Category<" in response.text


@pytest.mark.django_db
def test_the_index_counts_the_open_ones(signed_in):
    settings = reverse("settings")

    def value():
        return re.search(
            r'>Categories</span>.*?<span class="row-value">([^<]+)<',
            signed_in.get(settings).text,
            re.DOTALL,
        )[1]

    assert value() == "None yet"
    category(closed=True)
    assert value() == "None open"
    category("Rent")
    category("Fuel")
    assert value() == "2 open"


@pytest.mark.django_db
@pytest.mark.parametrize("page", ["", "edit_"])
def test_the_one_open_is_marked_current(signed_in, page):
    groceries = category()

    response = signed_in.get(url(page, groceries))

    current = [c for c in tags(response, "a") if c.get("aria-current")]
    assert {c["href"] for c in current if c["class"] in {"row", "side-link"}} == {
        url("", groceries),
        CATEGORIES,
    }


@pytest.mark.django_db
def test_one_goes_back_to_its_list(signed_in):
    groceries = category()

    response = signed_in.get(url("", groceries))

    assert tags(response, "a", href=CATEGORIES, **{"aria-label": "Back to Categories"})


@pytest.mark.django_db
@pytest.mark.parametrize("action", ["close_", "reopen_", "delete_"])
def test_each_action_needs_a_post(signed_in, action):
    groceries = category()

    assert signed_in.get(url(action, groceries)).status_code == 405


@pytest.mark.django_db
@pytest.mark.parametrize("page", ["", "edit_"])
def test_every_page_needs_signing_in(client, page):
    groceries = category()

    for response in [client.get(NEW), client.get(url(page, groceries))]:
        assert response["Location"].startswith(reverse("sign_in"))


@pytest.mark.django_db
@pytest.mark.parametrize("action", ["close_", "reopen_", "delete_"])
def test_each_action_needs_signing_in(client, action):
    groceries = category()

    response = client.post(url(action, groceries))

    assert response["Location"].startswith(reverse("sign_in"))
    assert Category.objects.get() == groceries
