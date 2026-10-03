import re
from html import unescape

import pytest
from django.db import DatabaseError
from django.urls import reverse
from django.utils.timezone import localdate

from apps.core.models import HistoryEntry
from apps.masters.models import Account
from apps.masters.testing import add, edit


def actions(response):
    return re.findall(r"data-history-action>([^<]+)<", response.text)


def changes(response):
    found = re.findall(r"data-history-change>([^<]+)<", response.text)
    return [unescape(change) for change in found]


def detail(client, account):
    return client.get(reverse("masters:asset", args=[account.pk]))


@pytest.mark.django_db
def test_creating_an_asset_account_is_in_its_history(signed_in):
    page = signed_in.get(add(signed_in)["Location"])

    assert actions(page) == ["Created"]


@pytest.mark.django_db
def test_editing_an_asset_account_lists_each_changed_field(signed_in, hdfc):
    edit(
        signed_in,
        hdfc,
        name="HDFC Salary",
        kind="deposit",
        opening_balance="1500.5",
        notes="Joint",
    )

    page = detail(signed_in, hdfc)
    assert actions(page) == ["Edited"]
    assert changes(page) == [
        "Name: HDFC → HDFC Salary",
        "Kind: Bank → Deposit",
        "Opening balance: ₹3,20,000.00 → ₹1,500.50",
        "Notes: None → Joint",
    ]


@pytest.mark.django_db
def test_an_asset_accounts_history_is_newest_first(signed_in):
    account_url = add(signed_in, name="HDFC")["Location"]
    account = Account.objects.get()
    edit(signed_in, account, name="HDFC Salary")
    edit(signed_in, Account.objects.get(), opened_on="2026-01-02")

    page = signed_in.get(account_url)

    assert actions(page) == ["Edited", "Edited", "Created"]
    assert changes(page) == [
        f"Opened on: {localdate():%-d %b %Y} → 2 Jan 2026",
        "Name: HDFC → HDFC Salary",
    ]


@pytest.mark.django_db
def test_saving_an_asset_account_unchanged_adds_nothing(signed_in, hdfc):
    edit(signed_in, hdfc, opening_balance="320000.00")

    assert actions(detail(signed_in, hdfc)) == []


@pytest.mark.django_db
def test_an_asset_account_isnt_saved_unless_its_history_is(
    signed_in, hdfc, monkeypatch
):
    def fail(*args, **kwargs):
        raise DatabaseError

    monkeypatch.setattr(HistoryEntry.objects, "create", fail)

    with pytest.raises(DatabaseError):
        add(signed_in, name="ICICI")
    with pytest.raises(DatabaseError):
        edit(signed_in, hdfc, name="HDFC Salary")

    assert list(Account.objects.values_list("name", flat=True)) == ["HDFC"]
