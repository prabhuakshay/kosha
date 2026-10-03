import re

import pytest
from django.urls import reverse

from apps.core.testing import tags
from apps.masters.models import Account

ASSETS = reverse("masters:assets")


def asset(name, kind, balance):
    return Account.objects.create(
        type=Account.Type.ASSET, kind=kind, name=name, opening_balance=balance
    )


def groups(response):
    """Each Kind's label and subtotal, then its rows' names and balances."""
    return re.findall(
        r'data-kind>([^<]+)</span><span class="amount" data-subtotal="\w+">([^<]+)<',
        response.text,
    )


def rows(response):
    return re.findall(
        r'font-semibold">([^<]+)</span>\s*<span class="amount text-\[14px\]" '
        r"data-balance>([^<]+)<",
        response.text,
    )


@pytest.mark.django_db
def test_assets_are_grouped_by_kind_with_subtotals_and_a_total(signed_in):
    asset("Gold", "property", "500000")
    asset("ICICI", "bank", "20000")
    asset("hdfc", "bank", "300000")
    asset("Ravi", "lent", "5000")
    asset("Wallet", "cash", "-250")

    response = signed_in.get(ASSETS)

    assert groups(response) == [
        ("Bank", "₹3,20,000.00"),
        ("Cash", "-₹250.00"),
        ("Lent", "₹5,000.00"),
        ("Property", "₹5,00,000.00"),
    ]
    assert rows(response) == [
        ("hdfc", "₹3,00,000.00"),
        ("ICICI", "₹20,000.00"),
        ("Wallet", "-₹250.00"),
        ("Ravi", "₹5,000.00"),
        ("Gold", "₹5,00,000.00"),
    ]
    assert "data-total>₹8,24,750.00<" in response.text


@pytest.mark.django_db
def test_amounts_are_written_in_the_base_currency(signed_in):
    asset("Chase", "bank", "320000")
    signed_in.post(reverse("base_currency"), {"base_currency": "USD"})

    response = signed_in.get(ASSETS)

    assert groups(response) == [("Bank", "$320,000.00")]


@pytest.mark.django_db
def test_each_row_shows_its_kinds_icon(signed_in):
    account = asset("Gold", "property", "1")

    response = signed_in.get(ASSETS)

    assert re.search(
        rf'href="{reverse("masters:asset", args=[account.pk])}" class="row" >\s*'
        r'<span class="tile"><i data-lucide="house">',
        response.text,
    )


def selected_rows(response):
    return [
        r["href"]
        for r in tags(response, "a", **{"class": "row"})
        if r.get("aria-current") == "page"
    ]


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["masters:asset", "masters:edit_asset"])
def test_the_account_open_is_marked_current_in_the_list(signed_in, name):
    hdfc, other = asset("HDFC", "bank", "1"), asset("ICICI", "bank", "1")

    response = signed_in.get(reverse(name, args=[hdfc.pk]))

    assert selected_rows(response) == [reverse("masters:asset", args=[hdfc.pk])]
    assert tags(response, "a", href=reverse("masters:asset", args=[other.pk]))
    current = tags(response, "a", **{"class": "sub-link", "aria-current": "page"})
    assert {c["href"] for c in current} == {ASSETS}


@pytest.mark.django_db
def test_an_account_goes_back_to_the_assets_list(signed_in):
    hdfc = asset("HDFC", "bank", "1")

    response = signed_in.get(reverse("masters:asset", args=[hdfc.pk]))

    assert tags(response, "a", href=ASSETS, **{"aria-label": "Back to Assets"})


@pytest.mark.django_db
def test_only_asset_accounts_open_as_assets(signed_in):
    shop = Account.objects.create(type=Account.Type.EXPENSE, name="Amazon")

    response = signed_in.get(reverse("masters:asset", args=[shop.pk]))

    assert response.status_code == 404
