import re

import pytest
from django.urls import reverse

from apps.core.testing import tags
from apps.masters.models import Account
from apps.masters.testing import account, edit, errors, history, listed, notices, url

ASSET, LIABILITY = Account.Type.ASSET, Account.Type.LIABILITY
EXPENSE, INCOME = Account.Type.EXPENSE, Account.Type.INCOME
EVERY_TYPE = [ASSET, LIABILITY, EXPENSE, INCOME]
WITH_BALANCE = [ASSET, LIABILITY]


def detail(client, of):
    return client.get(url("", of))


@pytest.mark.django_db
@pytest.mark.parametrize("type_", WITH_BALANCE)
def test_one_with_a_balance_cant_be_closed_and_says_why(signed_in, type_):
    hdfc = account(type_, balance=320000)

    response = signed_in.post(url("close_", hdfc), follow=True)

    hdfc.refresh_from_db()
    assert not hdfc.closed
    assert notices(response) == [
        (
            "HDFC can't be closed while its balance is ₹3,20,000.00. "
            "Only an account with a zero balance can be closed."
        )
    ]


@pytest.mark.django_db
@pytest.mark.parametrize("type_", WITH_BALANCE)
def test_one_with_a_balance_offers_no_close_and_says_why(signed_in, type_):
    hdfc = account(type_, balance=-500)

    response = detail(signed_in, hdfc)

    assert not tags(response, "form", action=url("close_", hdfc))
    assert "Only an account with a zero balance can be closed." in response.text


@pytest.mark.django_db
@pytest.mark.parametrize("type_", EVERY_TYPE)
def test_one_with_nothing_in_it_is_closed_into_the_closed_section(signed_in, type_):
    hdfc = account(type_)
    account(type_, "ICICI")

    response = signed_in.post(url("close_", hdfc), follow=True)

    hdfc.refresh_from_db()
    assert hdfc.closed
    assert notices(response) == ["Closed HDFC."]
    assert listed(signed_in, type_) == (["ICICI"], ["HDFC"])


@pytest.mark.django_db
@pytest.mark.parametrize("type_", [EXPENSE, INCOME])
def test_an_expense_or_income_account_can_always_be_closed(signed_in, type_):
    amazon = Account.objects.create(type=type_, name="Amazon", opening_balance=5)

    signed_in.post(url("close_", amazon))

    amazon.refresh_from_db()
    assert amazon.closed


@pytest.mark.django_db
@pytest.mark.parametrize("type_", EVERY_TYPE)
def test_the_closed_section_starts_collapsed(signed_in, type_):
    account(type_, closed=True)

    response = signed_in.get(reverse("masters:accounts"))

    section = tags(response, "details")
    assert len(section) == 1
    assert "open" not in section[0]
    assert "Closed" in response.text


@pytest.mark.django_db
@pytest.mark.parametrize("type_", EVERY_TYPE)
def test_the_closed_section_is_open_while_one_in_it_is(signed_in, type_):
    hdfc = account(type_, closed=True)

    response = detail(signed_in, hdfc)

    assert "open" in tags(response, "details")[0]
    assert tags(response, "a", href=url("", hdfc), **{"aria-current": "page"})


@pytest.mark.django_db
@pytest.mark.parametrize("type_", EVERY_TYPE)
def test_a_list_with_none_closed_has_no_closed_section(signed_in, type_):
    account(type_)

    response = signed_in.get(reverse("masters:accounts"))

    assert not tags(response, "details")


@pytest.mark.django_db
@pytest.mark.parametrize("type_", EVERY_TYPE)
def test_a_list_of_only_closed_ones_isnt_empty(signed_in, type_):
    account(type_, closed=True)

    response = signed_in.get(reverse("masters:accounts"))

    assert "yet</h1>" not in response.text
    assert listed(signed_in, type_) == ([], ["HDFC"])


@pytest.mark.django_db
@pytest.mark.parametrize("type_", EVERY_TYPE)
def test_a_closed_one_is_reopened(signed_in, type_):
    hdfc = account(type_, closed=True)

    response = signed_in.post(url("reopen_", hdfc), follow=True)

    hdfc.refresh_from_db()
    assert not hdfc.closed
    assert notices(response) == ["Reopened HDFC."]
    assert listed(signed_in, type_) == (["HDFC"], [])


def sheet_for(response, action):
    """The confirm sheet a form posting to ``action`` sits in, by its id.

    Its Cancel button, which takes the focus, hides the sheet.
    """
    form = re.search(
        rf'<form [^>]*action="{action}".*?</form>', response.text, re.DOTALL
    )
    cancel = form and re.search(
        r'popovertarget="([\w-]+)" popovertargetaction="hide"[^>]*autofocus', form[0]
    )
    return cancel and cancel[1]


@pytest.mark.django_db
@pytest.mark.parametrize("type_", EVERY_TYPE)
@pytest.mark.parametrize("action", ["close_", "delete_"])
def test_close_and_delete_ask_first(signed_in, type_, action):
    hdfc = account(type_)

    response = detail(signed_in, hdfc)

    sheet = sheet_for(response, url(action, hdfc))
    assert "popover" in tags(response, "div", id=sheet)[0]
    assert tags(response, "button", popovertarget=sheet, type="button")


@pytest.mark.django_db
@pytest.mark.parametrize("type_", EVERY_TYPE)
def test_reopen_doesnt_ask_first(signed_in, type_):
    hdfc = account(type_, closed=True)

    response = detail(signed_in, hdfc)

    assert tags(response, "form", method="post", action=url("reopen_", hdfc))
    assert not sheet_for(response, url("reopen_", hdfc))
    assert not tags(response, "form", action=url("close_", hdfc))


@pytest.mark.django_db
@pytest.mark.parametrize("type_", EVERY_TYPE)
def test_a_closed_one_says_so(signed_in, type_):
    hdfc = account(type_, closed=True)

    response = detail(signed_in, hdfc)

    assert "data-closed-badge" in response.text


@pytest.mark.django_db
@pytest.mark.parametrize("type_", EVERY_TYPE)
def test_closing_and_reopening_are_in_its_history(signed_in, type_):
    hdfc = account(type_)

    signed_in.post(url("close_", hdfc))
    signed_in.post(url("reopen_", hdfc))

    assert history(detail(signed_in, hdfc)) == (["Reopened", "Closed"], [])


@pytest.mark.django_db
def test_closing_one_already_closed_adds_nothing(signed_in):
    hdfc = account(ASSET, closed=True)

    signed_in.post(url("close_", hdfc))
    hdfc.closed = False
    hdfc.save()
    signed_in.post(url("reopen_", hdfc))

    assert history(detail(signed_in, hdfc)) == ([], [])


@pytest.mark.django_db
def test_a_closed_ones_balance_cant_be_edited_away_from_zero(signed_in):
    hdfc = account(ASSET, closed=True)

    response = edit(signed_in, hdfc, opening_balance="500")

    assert errors(response) == [
        "A closed account's balance must stay zero. Reopen it first."
    ]
    hdfc.refresh_from_db()
    assert hdfc.opening_balance == 0


@pytest.mark.django_db
def test_a_closed_one_can_still_be_renamed(signed_in):
    hdfc = account(ASSET, closed=True)

    edit(signed_in, hdfc, name="HDFC Old")

    hdfc.refresh_from_db()
    assert hdfc.name == "HDFC Old"


def accounts_value(response):
    return re.search(
        r'>Accounts</span>.*?<span class="row-value">([^<]+)<',
        response.text,
        re.DOTALL,
    )[1]


@pytest.mark.django_db
def test_closed_ones_dont_count_in_settings(signed_in):
    account(ASSET, balance=320000)
    account(ASSET, "Old savings", closed=True)
    account(EXPENSE, "Amazon")
    account(EXPENSE, "Old shop", closed=True)

    response = signed_in.get(reverse("settings"))

    assert accounts_value(response) == "2 open"


@pytest.mark.django_db
def test_only_closed_ones_says_none_open_in_settings(signed_in):
    account(LIABILITY, closed=True)

    response = signed_in.get(reverse("settings"))

    assert accounts_value(response) == "None open"


@pytest.mark.django_db
def test_closed_ones_dont_count_in_list_totals(signed_in):
    account(ASSET, balance=320000)
    account(ASSET, "Old savings", closed=True)

    response = signed_in.get(reverse("masters:accounts"))

    assert re.findall(r'data-subtotal="bank">([^<]+)<', response.text) == [
        "₹3,20,000.00"
    ]
    assert listed(signed_in, ASSET) == (["HDFC"], ["Old savings"])


@pytest.mark.django_db
@pytest.mark.parametrize("type_", EVERY_TYPE)
@pytest.mark.parametrize("action", ["close_", "reopen_", "delete_"])
def test_each_action_needs_a_post(signed_in, type_, action):
    hdfc = account(type_)

    assert signed_in.get(url(action, hdfc)).status_code == 405


@pytest.mark.django_db
@pytest.mark.parametrize("action", ["close_", "reopen_", "delete_"])
def test_each_action_needs_signing_in(client, action):
    hdfc = account(ASSET)

    response = client.post(url(action, hdfc))

    assert response["Location"].startswith(reverse("sign_in"))
    assert Account.objects.get() == hdfc


@pytest.mark.django_db
@pytest.mark.parametrize("action", ["close_", "reopen_", "delete_"])
def test_each_action_finds_only_its_own_type(signed_in, action):
    amazon = account(EXPENSE, "Amazon")

    response = signed_in.post(
        reverse(f"masters:{action}income_account", args=[amazon.pk])
    )

    assert response.status_code == 404
