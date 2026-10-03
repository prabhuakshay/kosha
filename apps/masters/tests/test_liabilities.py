import re
from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils.timezone import localdate

from apps.core.testing import tags
from apps.masters.models import Account
from apps.masters.testing import (
    add,
    edit,
    errors,
    field_value,
    groups,
    history,
    rows,
)

LIABILITY = Account.Type.LIABILITY
LIABILITIES, NEW = reverse("masters:liabilities"), reverse("masters:new_liability")


def liability(name, kind, balance):
    return Account.objects.create(
        type=LIABILITY,
        kind=kind,
        name=name,
        opening_balance=balance,
        opened_on=localdate(),
    )


def detail(client, account):
    return client.get(reverse("masters:liability", args=[account.pk]))


@pytest.mark.django_db
def test_the_owner_adds_a_liability_and_sees_it(signed_in):
    response = add(
        signed_in,
        LIABILITY,
        name="HDFC Regalia",
        kind="credit_card",
        opening_balance="45000.50",
        opened_on="2026-04-01",
        notes="Due on the 5th",
    )

    account = Account.objects.get()
    assert account.type == LIABILITY
    assert response["Location"] == reverse("masters:liability", args=[account.pk])
    page = signed_in.get(response["Location"])
    assert '<h1 class="display page-title">HDFC Regalia</h1>' in page.text
    assert "data-kind>Credit card</span> · Liability<" in page.text
    assert "data-balance>₹45,000.50<" in page.text
    assert "1 Apr 2026" in page.text
    assert "Due on the 5th" in page.text


@pytest.mark.django_db
def test_a_new_liability_opens_today_owing_nothing(signed_in):
    response = signed_in.get(NEW)

    assert field_value(response, "opening_balance") == "0"
    assert field_value(response, "opened_on") == localdate().isoformat()


@pytest.mark.django_db
def test_a_liabilitys_opening_date_cant_be_in_the_future(signed_in):
    tomorrow = localdate() + timedelta(days=1)

    response = add(signed_in, LIABILITY, opened_on=tomorrow.isoformat())

    assert errors(response) == ["The opening date can't be in the future."]
    assert not Account.objects.exists()


@pytest.mark.django_db
def test_a_liabilitys_opening_balance_has_the_base_currencys_places(signed_in):
    signed_in.post(reverse("base_currency"), {"base_currency": "JPY"})

    response = add(signed_in, LIABILITY, opening_balance="10.5")

    assert errors(response) == ["Amounts in JPY have no decimal places."]
    assert not Account.objects.exists()


@pytest.mark.django_db
def test_a_liability_in_credit_has_a_negative_opening_balance(signed_in):
    response = add(signed_in, LIABILITY, opening_balance="-1500")

    page = signed_in.get(response["Location"])
    assert Account.objects.get().opening_balance == Decimal(-1500)
    assert "data-balance>-₹1,500.00<" in page.text


@pytest.mark.django_db
def test_only_liability_kinds_are_offered(signed_in):
    response = signed_in.get(NEW)

    offered = [o["value"] for o in tags(response, "option")]
    assert offered == ["credit_card", "loan", "mortgage", "debt"]


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ["bank", "lent", ""])
def test_a_liability_cant_have_an_asset_kind(signed_in, kind):
    response = add(signed_in, LIABILITY, kind=kind)

    assert response.status_code == 200
    assert not Account.objects.exists()


@pytest.mark.django_db
def test_an_asset_account_cant_be_added_with_a_liability_kind(signed_in):
    response = add(signed_in, kind="mortgage")

    assert response.status_code == 200
    assert not Account.objects.exists()


@pytest.mark.django_db
def test_two_liabilities_cant_share_a_name_ignoring_case(signed_in):
    add(signed_in, LIABILITY, name="HDFC Regalia")

    response = add(signed_in, LIABILITY, name="hdfc regalia")

    assert errors(response) == ["There's already a Liability called “HDFC Regalia”."]
    assert Account.objects.count() == 1


@pytest.mark.django_db
def test_a_liability_may_share_a_name_with_an_asset_account(signed_in):
    add(signed_in, name="HDFC")

    response = add(signed_in, LIABILITY, name="hdfc")

    assert response.status_code == 302
    assert Account.objects.filter(name__iexact="hdfc").count() == 2


@pytest.mark.django_db
def test_the_owner_edits_a_liability_and_changes_its_kind(signed_in):
    card = liability("HDFC", "credit_card", "45000")

    response = edit(
        signed_in, card, name="HDFC Home", kind="mortgage", opening_balance="2500000"
    )

    assert response["Location"] == reverse("masters:liability", args=[card.pk])
    card.refresh_from_db()
    assert (card.type, card.name, card.kind, card.opening_balance) == (
        LIABILITY,
        "HDFC Home",
        "mortgage",
        2500000,
    )


@pytest.mark.django_db
def test_the_liability_edit_form_shows_it_as_it_is(signed_in):
    card = liability("HDFC", "loan", "45000")

    response = signed_in.get(reverse("masters:edit_liability", args=[card.pk]))

    assert field_value(response, "name") == "HDFC"
    assert field_value(response, "opening_balance") == "45000.00"
    assert [o["value"] for o in tags(response, "option") if "selected" in o] == ["loan"]


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ["bank", "property"])
def test_a_liability_cant_become_an_asset_account(signed_in, kind):
    card = liability("HDFC", "credit_card", "45000")

    response = edit(signed_in, card, kind=kind)

    assert response.status_code == 200
    card.refresh_from_db()
    assert (card.type, card.kind) == (LIABILITY, "credit_card")


@pytest.mark.django_db
def test_an_edit_cant_take_another_liabilitys_name(signed_in):
    card = liability("HDFC", "credit_card", "1")
    liability("SBI Card", "credit_card", "1")

    response = edit(signed_in, card, name="sbi card")

    assert errors(response) == ["There's already a Liability called “SBI Card”."]


@pytest.mark.django_db
def test_liabilities_are_grouped_by_kind_with_subtotals_and_a_total_owed(signed_in):
    liability("Home loan", "mortgage", "2500000")
    liability("SBI Card", "credit_card", "20000")
    liability("hdfc", "credit_card", "-500")
    liability("Ravi", "debt", "5000")

    response = signed_in.get(LIABILITIES)

    assert groups(response) == [
        ("Credit card", "₹19,500.00"),
        ("Mortgage", "₹25,00,000.00"),
        ("Debt", "₹5,000.00"),
    ]
    assert rows(response) == [
        ("hdfc", "-₹500.00"),
        ("SBI Card", "₹20,000.00"),
        ("Home loan", "₹25,00,000.00"),
        ("Ravi", "₹5,000.00"),
    ]
    assert "Total owed" in response.text
    assert "data-total>₹25,24,500.00<" in response.text


@pytest.mark.django_db
def test_the_liabilities_list_leaves_out_asset_accounts(signed_in):
    Account.objects.create(type=Account.Type.ASSET, kind="bank", name="HDFC")

    response = signed_in.get(LIABILITIES)

    assert rows(response) == []
    assert "No liabilities yet</h1>" in response.text


@pytest.mark.django_db
def test_each_liability_row_shows_its_kinds_icon(signed_in):
    card = liability("HDFC", "credit_card", "1")

    response = signed_in.get(LIABILITIES)

    assert re.search(
        rf'href="{reverse("masters:liability", args=[card.pk])}" class="row" >\s*'
        r'<span class="tile"><i data-lucide="credit-card">',
        response.text,
    )


@pytest.mark.django_db
def test_an_empty_liabilities_list_offers_the_first_one(signed_in):
    response = signed_in.get(LIABILITIES)

    assert tags(response, "a", href=NEW, **{"class": "btn"})


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["masters:liability", "masters:edit_liability"])
def test_the_liability_open_is_marked_current(signed_in, name):
    card = liability("HDFC", "credit_card", "1")

    response = signed_in.get(reverse(name, args=[card.pk]))

    current = tags(response, "a", **{"aria-current": "page"})
    assert {c["href"] for c in current if c["class"] in {"row", "sub-link"}} == {
        reverse("masters:liability", args=[card.pk]),
        LIABILITIES,
    }


@pytest.mark.django_db
def test_a_liability_goes_back_to_the_liabilities_list(signed_in):
    card = liability("HDFC", "credit_card", "1")

    response = detail(signed_in, card)

    assert tags(
        response, "a", href=LIABILITIES, **{"aria-label": "Back to Liabilities"}
    )


@pytest.mark.django_db
def test_only_liabilities_open_as_liabilities(signed_in, hdfc):
    assert detail(signed_in, hdfc).status_code == 404
    card = liability("HDFC", "credit_card", "1")
    assert signed_in.get(reverse("masters:asset", args=[card.pk])).status_code == 404


@pytest.mark.django_db
def test_creating_and_editing_a_liability_is_in_its_history(signed_in):
    add(signed_in, LIABILITY, name="HDFC", kind="credit_card", opening_balance="100")
    card = Account.objects.get()
    edit(signed_in, card, kind="loan", opening_balance="-20")

    assert history(detail(signed_in, card)) == (
        ["Edited", "Created"],
        ["Kind: Credit card → Loan", "Opening balance: ₹100.00 → -₹20.00"],
    )


@pytest.mark.django_db
def test_the_full_history_says_a_liability_changed(signed_in):
    add(signed_in, LIABILITY, name="HDFC")

    response = signed_in.get(reverse("history"))

    assert "data-history-subject>HDFC · Liability<" in response.text
