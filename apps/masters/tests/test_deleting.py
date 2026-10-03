import re

import pytest
from django.urls import reverse

from apps.core.testing import tags
from apps.masters.listings import LISTINGS
from apps.masters.models import Account
from apps.masters.testing import account, listed, notices, url

ASSET, LIABILITY = Account.Type.ASSET, Account.Type.LIABILITY
EXPENSE, INCOME = Account.Type.EXPENSE, Account.Type.INCOME
EVERY_TYPE = [ASSET, LIABILITY, EXPENSE, INCOME]


@pytest.mark.django_db
@pytest.mark.parametrize("type_", EVERY_TYPE)
def test_an_unused_one_is_deleted(signed_in, type_):
    hdfc = account(type_, balance=0)

    response = signed_in.post(url("delete_", hdfc), follow=True)

    assert not Account.objects.exists()
    assert response.redirect_chain[-1][0] == reverse(LISTINGS[type_].list)
    assert notices(response) == ["Deleted HDFC."]
    assert listed(signed_in, type_) == ([], [])


@pytest.mark.django_db
def test_one_with_a_balance_can_still_be_deleted(signed_in):
    hdfc = account(ASSET, balance=320000)

    signed_in.post(url("delete_", hdfc))

    assert not Account.objects.exists()


@pytest.mark.django_db
def test_one_something_refers_to_cant_be_deleted(signed_in, monkeypatch):
    hdfc = account(ASSET)
    monkeypatch.setattr(Account, "in_use", property(lambda _: True))

    response = signed_in.post(url("delete_", hdfc), follow=True)

    assert Account.objects.get() == hdfc
    assert notices(response) == [
        "HDFC can't be deleted while anything refers to it. Close it instead."
    ]
    assert not tags(response, "form", action=url("delete_", hdfc))


@pytest.mark.django_db
@pytest.mark.parametrize("type_", EVERY_TYPE)
def test_the_full_history_still_names_a_deleted_one(signed_in, type_):
    hdfc = account(type_)

    signed_in.post(url("delete_", hdfc))

    response = signed_in.get(reverse("history"))
    assert re.findall(r"data-history-action>([^<]+)<", response.text) == ["Deleted"]
    assert f"data-history-subject>HDFC · {type_.label}<" in response.text
