from typing import NamedTuple

import pytest
from django.urls import reverse

from apps.core.testing import tags
from apps.masters.models import Account
from apps.masters.testing import add, edit, errors, history, listed

EXPENSE, INCOME = Account.Type.EXPENSE, Account.Type.INCOME


class List(NamedTuple):
    type: Account.Type
    title: str
    plural: str
    route: str
    noun: str


LISTS = [
    pytest.param(
        List(EXPENSE, "Expenses", "expenses", "expense_account", "an Expense account"),
        id="expense",
    ),
    pytest.param(
        List(INCOME, "Income", "income", "income_account", "an Income account"),
        id="income",
    ),
]


def account(type_, name, notes=""):
    return Account.objects.create(type=type_, name=name, notes=notes)


def status(client, route, of):
    return client.get(reverse(f"masters:{route}", args=[of.pk])).status_code


@pytest.mark.django_db
@pytest.mark.parametrize("listing", LISTS)
def test_the_owner_adds_one_and_sees_it(signed_in, listing):
    response = add(signed_in, listing.type, name="Amazon", notes="Prime too")

    created = Account.objects.get()
    assert created.type == listing.type
    assert response["Location"] == reverse(
        f"masters:{listing.route}", args=[created.pk]
    )
    page = signed_in.get(response["Location"])
    assert "<h1>Amazon</h1>" in page.text
    assert f"{created.get_type_display()}</p>" in page.text
    assert "Prime too" in page.text
    assert "data-balance" not in page.text


@pytest.mark.django_db
@pytest.mark.parametrize("listing", LISTS)
def test_the_form_asks_for_no_kind_or_opening_balance(signed_in, listing):
    response = signed_in.get(reverse(f"masters:new_{listing.route}"))

    assert tags(response, "input", name="name")
    assert tags(response, "textarea", name="notes")
    assert not tags(response, "select", name="kind")
    assert not tags(response, "input", name="opening_balance")
    assert not tags(response, "input", name="opened_on")


@pytest.mark.django_db
@pytest.mark.parametrize("listing", LISTS)
def test_a_kind_or_opening_balance_posted_anyway_is_ignored(signed_in, listing):
    add(
        signed_in,
        listing.type,
        kind="bank",
        opening_balance="500",
        opened_on="2026-01-01",
    )

    created = Account.objects.get()
    assert (created.kind, created.opening_balance, created.opened_on) == ("", 0, None)


@pytest.mark.django_db
@pytest.mark.parametrize("listing", LISTS)
def test_they_are_listed_alphabetically_ignoring_case(signed_in, listing):
    account(listing.type, "Zomato")
    account(listing.type, "amazon")
    account(listing.type, "BESCOM")

    assert listed(signed_in, listing.type)[0] == ["amazon", "BESCOM", "Zomato"]


@pytest.mark.django_db
@pytest.mark.parametrize("listing", LISTS)
def test_a_list_leaves_out_other_types(signed_in, listing):
    account(EXPENSE if listing.type == INCOME else INCOME, "Amazon")
    Account.objects.create(type=Account.Type.ASSET, kind="bank", name="HDFC")

    assert listed(signed_in, listing.type)[0] == []


@pytest.mark.django_db
@pytest.mark.parametrize("listing", LISTS)
def test_an_empty_list_offers_the_first_one(signed_in, listing):
    response = signed_in.get(reverse("masters:accounts"))

    assert tags(
        response,
        "a",
        href=reverse(f"masters:new_{listing.route}"),
        **{"class": "group row"},
    )


@pytest.mark.django_db
@pytest.mark.parametrize("listing", LISTS)
def test_two_of_a_type_cant_share_a_name_ignoring_case(signed_in, listing):
    add(signed_in, listing.type, name="Amazon")

    response = add(signed_in, listing.type, name="AMAZON")

    assert errors(response) == [f"There's already {listing.noun} called “Amazon”."]
    assert Account.objects.count() == 1


@pytest.mark.django_db
def test_an_expense_and_an_income_account_may_share_a_name(signed_in):
    add(signed_in, EXPENSE, name="Amazon")

    response = add(signed_in, INCOME, name="amazon")

    assert response.status_code == 302
    assert Account.objects.filter(name__iexact="amazon").count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize("listing", LISTS)
def test_the_owner_edits_one(signed_in, listing):
    amazon = account(listing.type, "Amazon")

    response = edit(signed_in, amazon, name="Amazon India", notes="Refunds too")

    assert response["Location"] == reverse(f"masters:{listing.route}", args=[amazon.pk])
    amazon.refresh_from_db()
    assert (amazon.type, amazon.name, amazon.notes) == (
        listing.type,
        "Amazon India",
        "Refunds too",
    )


@pytest.mark.django_db
@pytest.mark.parametrize("listing", LISTS)
def test_an_edit_cant_take_another_ones_name(signed_in, listing):
    amazon = account(listing.type, "Amazon")
    account(listing.type, "Flipkart")

    response = edit(signed_in, amazon, name="flipkart")

    assert errors(response) == [f"There's already {listing.noun} called “Flipkart”."]


@pytest.mark.django_db
@pytest.mark.parametrize("listing", LISTS)
def test_creating_and_editing_one_is_in_its_history(signed_in, listing):
    add(signed_in, listing.type, name="Amazon")
    amazon = Account.objects.get()
    edit(signed_in, amazon, name="Amazon India", notes="Refunds")

    page = signed_in.get(reverse(f"masters:{listing.route}", args=[amazon.pk]))

    assert history(page) == (
        ["Edited", "Created"],
        ["Name: Amazon → Amazon India", "Notes: None → Refunds"],
    )


@pytest.mark.django_db
@pytest.mark.parametrize("listing", LISTS)
def test_the_full_history_names_its_type(signed_in, listing):
    add(signed_in, listing.type, name="Amazon")

    response = signed_in.get(reverse("history"))

    assert f"data-history-subject>Amazon · {listing.type.label}<" in response.text


@pytest.mark.django_db
@pytest.mark.parametrize("listing", LISTS)
@pytest.mark.parametrize("page", ["", "edit_"])
def test_the_one_open_is_marked_current(signed_in, listing, page):
    amazon = account(listing.type, "Amazon")

    response = signed_in.get(
        reverse(f"masters:{page}{listing.route}", args=[amazon.pk])
    )

    current = [c for c in tags(response, "a") if c.get("aria-current")]
    assert {c["href"] for c in current if c["class"] in {"row", "side-link"}} == {
        reverse(f"masters:{listing.route}", args=[amazon.pk]),
        reverse("masters:accounts"),
    }


@pytest.mark.django_db
@pytest.mark.parametrize("listing", LISTS)
def test_one_goes_back_to_the_accounts_list(signed_in, listing):
    amazon = account(listing.type, "Amazon")

    response = signed_in.get(reverse(f"masters:{listing.route}", args=[amazon.pk]))

    assert tags(
        response,
        "a",
        href=reverse("masters:accounts"),
        **{"aria-label": "Back to Accounts"},
    )


@pytest.mark.django_db
def test_each_opens_only_as_its_own_type(signed_in, hdfc):
    amazon = account(EXPENSE, "Amazon")
    acme = account(INCOME, "Acme")

    assert status(signed_in, "income_account", amazon) == 404
    assert status(signed_in, "expense_account", acme) == 404
    assert status(signed_in, "expense_account", hdfc) == 404
    assert status(signed_in, "asset", amazon) == 404
