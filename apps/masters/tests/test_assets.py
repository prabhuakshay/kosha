from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils.timezone import localdate

from apps.core.testing import tags
from apps.masters.models import Account
from apps.masters.testing import add, edit, errors, field_value

ACCOUNTS, NEW = reverse("masters:accounts"), reverse("masters:new_asset")


@pytest.mark.django_db
def test_the_owner_adds_an_asset_account_and_sees_it(signed_in):
    response = add(
        signed_in,
        name="HDFC FD",
        kind="deposit",
        opening_balance="320000.50",
        opened_on="2026-04-01",
        notes="Salary comes in here",
    )

    account = Account.objects.get()
    assert response["Location"] == reverse("masters:asset", args=[account.pk])
    page = signed_in.get(response["Location"])
    assert "<h1>HDFC FD</h1>" in page.text
    assert "data-kind>Deposit<" in page.text
    assert "data-balance>₹3,20,000.50<" in page.text
    assert "1 Apr 2026" in page.text
    assert "Salary comes in here" in page.text


@pytest.mark.django_db
def test_a_new_asset_account_opens_today_with_nothing_in_it(signed_in):
    response = signed_in.get(NEW)

    assert field_value(response, "opening_balance") == "0"
    assert field_value(response, "opened_on") == localdate().isoformat()


@pytest.mark.django_db
def test_the_opening_date_cant_be_in_the_future(signed_in):
    tomorrow = localdate() + timedelta(days=1)

    response = add(signed_in, opened_on=tomorrow.isoformat())

    assert errors(response) == ["The opening date can't be in the future."]
    assert not Account.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("currency", "amount", "error"),
    [
        ("INR", "10.005", "Amounts in INR have at most 2 decimal places."),
        ("JPY", "10.5", "Amounts in JPY have no decimal places."),
        ("KWD", "1.0005", "Amounts in KWD have at most 3 decimal places."),
    ],
)
def test_the_opening_balance_has_the_base_currencys_places(
    signed_in, currency, amount, error
):
    signed_in.post(reverse("base_currency"), {"base_currency": currency})

    response = add(signed_in, opening_balance=amount)

    assert errors(response) == [error]
    assert not Account.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("currency", "amount"),
    [("INR", "10.05"), ("INR", "10.500"), ("JPY", "1050.00"), ("KWD", "1.005")],
)
def test_an_opening_balance_to_the_base_currencys_places_is_kept(
    signed_in, currency, amount
):
    signed_in.post(reverse("base_currency"), {"base_currency": currency})

    add(signed_in, opening_balance=amount)

    assert Account.objects.get().opening_balance == Decimal(amount)


@pytest.mark.django_db
def test_an_overdrawn_account_has_a_negative_opening_balance(signed_in):
    response = add(signed_in, kind="bank", opening_balance="-1500")

    page = signed_in.get(response["Location"])
    assert "data-balance>-₹1,500.00<" in page.text


@pytest.mark.django_db
def test_only_asset_kinds_are_offered(signed_in):
    response = signed_in.get(NEW)

    offered = [o["value"] for o in tags(response, "option")]
    assert offered == ["bank", "deposit", "cash", "investment", "lent", "property"]


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ["credit_card", "", "salary"])
def test_any_other_kind_is_refused(signed_in, kind):
    response = add(signed_in, kind=kind)

    assert response.status_code == 200
    assert not Account.objects.exists()


@pytest.mark.django_db
def test_two_asset_accounts_cant_share_a_name_ignoring_case(signed_in):
    add(signed_in, name="HDFC Savings")

    response = add(signed_in, name="hdfc savings")

    assert errors(response) == [
        "There's already an Asset account called “HDFC Savings”."
    ]
    assert Account.objects.count() == 1


@pytest.mark.django_db
def test_an_asset_account_may_share_a_name_with_another_type(signed_in):
    Account.objects.create(type=Account.Type.EXPENSE, name="Amazon")

    add(signed_in, name="Amazon", kind="lent")

    assert Account.objects.filter(name="Amazon").count() == 2


@pytest.mark.django_db
def test_the_edit_form_shows_the_account_as_it_is(signed_in, hdfc):
    response = signed_in.get(reverse("masters:edit_asset", args=[hdfc.pk]))

    assert field_value(response, "name") == "HDFC"
    assert field_value(response, "opening_balance") == "320000.00"
    assert [o["value"] for o in tags(response, "option") if "selected" in o] == ["bank"]


@pytest.mark.django_db
def test_the_owner_edits_an_asset_account_and_changes_its_kind(signed_in, hdfc):
    response = edit(
        signed_in,
        hdfc,
        name="HDFC Salary",
        kind="deposit",
        opening_balance="1000",
        notes="Joint",
    )

    assert response["Location"] == reverse("masters:asset", args=[hdfc.pk])
    hdfc.refresh_from_db()
    assert (hdfc.name, hdfc.kind, hdfc.opening_balance, hdfc.notes) == (
        "HDFC Salary",
        "deposit",
        1000,
        "Joint",
    )


@pytest.mark.django_db
def test_an_asset_account_cant_become_a_liability(signed_in, hdfc):
    response = edit(signed_in, hdfc, kind="credit_card")

    assert response.status_code == 200
    hdfc.refresh_from_db()
    assert (hdfc.type, hdfc.kind) == (Account.Type.ASSET, "bank")


@pytest.mark.django_db
def test_an_asset_account_keeps_its_own_name_when_edited(signed_in, hdfc):
    response = edit(signed_in, hdfc, name="hdfc")

    assert response.status_code == 302
    hdfc.refresh_from_db()
    assert hdfc.name == "hdfc"


@pytest.mark.django_db
def test_an_edit_cant_take_another_asset_accounts_name(signed_in, hdfc):
    add(signed_in, name="ICICI")

    response = edit(signed_in, hdfc, name="icici")

    assert errors(response) == ["There's already an Asset account called “ICICI”."]
