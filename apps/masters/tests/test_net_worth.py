import re

import pytest
from django.urls import reverse

from apps.core.testing import tags
from apps.masters.models import Account

HOME = reverse("home")


def account(type_, kind, balance, name=None):
    return Account.objects.create(
        type=type_, kind=kind, name=name or kind, opening_balance=balance
    )


def asset(kind, balance, name=None):
    return account(Account.Type.ASSET, kind, balance, name)


def liability(kind, balance, name=None):
    return account(Account.Type.LIABILITY, kind, balance, name)


def amount(response, name):
    return re.search(rf"data-{name}>([^<]+)<", response.text)[1]


def link_around(response, name):
    return re.search(
        rf'<a href="([^"]+)"[^>]*>(?:(?!</a>).)*data-{name}>', response.text
    )[1]


@pytest.mark.django_db
def test_net_worth_is_every_asset_account_less_every_liability(signed_in):
    asset("bank", "300000")
    asset("lent", "5000")
    asset("property", "5000000")
    asset("cash", "-250")
    liability("credit_card", "40000")
    liability("mortgage", "3000000")
    liability("debt", "-1000")
    Account.objects.create(type=Account.Type.EXPENSE, name="Amazon")

    response = signed_in.get(HOME)

    assert amount(response, "net-worth") == "₹22,65,750.00"


@pytest.mark.django_db
def test_liquid_net_worth_counts_only_money_to_hand_less_credit_cards(signed_in):
    asset("bank", "300000")
    asset("deposit", "100000")
    asset("cash", "2000")
    asset("investment", "50000")
    asset("lent", "5000")
    asset("property", "5000000")
    liability("credit_card", "40000")
    liability("loan", "200000")

    response = signed_in.get(HOME)

    assert amount(response, "liquid") == "₹4,12,000.00"


@pytest.mark.django_db
def test_the_assets_and_liabilities_totals_lead_to_their_lists(signed_in):
    asset("bank", "300000")
    asset("property", "5000000")
    liability("credit_card", "40000")

    response = signed_in.get(HOME)

    assert amount(response, "assets") == "₹53,00,000.00"
    assert amount(response, "liabilities") == "₹40,000.00"
    accounts = reverse("masters:accounts")
    assert link_around(response, "assets") == f"{accounts}#assets"
    assert link_around(response, "liabilities") == f"{accounts}#liabilities"


@pytest.mark.django_db
def test_without_accounts_it_shows_zero_and_invites_the_first_asset_account(
    signed_in,
):
    response = signed_in.get(HOME)

    assert amount(response, "net-worth") == "₹0.00"
    assert tags(response, "a", href=reverse("masters:new_asset"))


@pytest.mark.django_db
def test_with_accounts_it_no_longer_invites_one(signed_in):
    liability("credit_card", "40000")

    response = signed_in.get(HOME)

    assert amount(response, "net-worth") == "-₹40,000.00"
    assert not tags(
        response, "a", href=reverse("masters:new_asset"), **{"class": "btn"}
    )


@pytest.mark.django_db
def test_amounts_are_written_in_the_base_currency(signed_in):
    asset("bank", "320000")
    signed_in.post(reverse("base_currency"), {"base_currency": "JPY"})

    response = signed_in.get(HOME)

    assert amount(response, "net-worth") == "¥320,000"
    assert amount(response, "liquid") == "¥320,000"


@pytest.mark.django_db
def test_closed_accounts_are_left_out_like_in_their_lists(signed_in):
    asset("bank", "300000")
    Account.objects.create(
        type=Account.Type.ASSET,
        kind="bank",
        name="Old bank",
        opening_balance="5000",
        closed=True,
    )

    response = signed_in.get(HOME)

    assert amount(response, "net-worth") == "₹3,00,000.00"
    assert amount(response, "assets") == "₹3,00,000.00"


@pytest.mark.django_db
def test_a_bar_shows_how_much_of_it_is_owned_and_how_much_owed(signed_in):
    asset("bank", "300000")
    liability("loan", "100000")

    response = signed_in.get(HOME)

    assert tags(response, "rect", **{"class": "worth-owned"})[0]["width"] == "75"


@pytest.mark.django_db
def test_without_accounts_there_is_no_bar(signed_in):
    response = signed_in.get(HOME)

    assert not tags(response, "rect")
