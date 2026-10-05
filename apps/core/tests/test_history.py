import re
from datetime import timedelta

import pytest
from django.contrib.contenttypes.models import ContentType
from django.db import DatabaseError
from django.urls import reverse
from django.utils.timezone import localdate

from apps.core.models import HistoryEntry, Setting
from apps.core.testing import shown_history as shown
from apps.masters.models import Account

HISTORY = reverse("history")


@pytest.mark.django_db
def test_changing_the_base_currency_is_in_history(signed_in):
    signed_in.post(reverse("base_currency"), {"base_currency": "USD"})

    assert shown(signed_in.get(HISTORY)) == [
        "Base currency changed Base currency · Setting Base currency: INR → USD"
    ]


@pytest.mark.django_db
def test_keeping_the_base_currency_adds_nothing(signed_in):
    signed_in.post(reverse("base_currency"), {"base_currency": "INR"})

    assert shown(signed_in.get(HISTORY)) == []


@pytest.mark.django_db
def test_history_shows_every_entry_with_its_subject(signed_in):
    signed_in.post(
        reverse("masters:new_asset"),
        {
            "name": "HDFC",
            "kind": "bank",
            "opening_balance": "0",
            "opened_on": localdate().isoformat(),
        },
    )
    signed_in.post(reverse("base_currency"), {"base_currency": "USD"})

    assert shown(signed_in.get(HISTORY)) == [
        "Base currency changed Base currency · Setting Base currency: INR → USD",
        "Created HDFC · Asset account",
    ]


def entry(at):
    return HistoryEntry.objects.create(
        at=at,
        action=HistoryEntry.Action.CREATED,
        subject_model=ContentType.objects.get_for_model(Account),
        subject_id=1,
        subject_type="Asset account",
        subject_name="HDFC",
    )


@pytest.mark.django_db
def test_history_is_grouped_by_day(signed_in, clock):
    for days_ago in (0, 1, 3):
        entry(clock.now - timedelta(days=days_ago))

    response = signed_in.get(HISTORY)

    earlier = localdate(clock.now - timedelta(days=3))
    assert re.findall(r"data-history-day>([^<]+)<", response.text) == [
        "Today",
        "Yesterday",
        f"{earlier:%-d %b %Y}",
    ]


@pytest.mark.django_db
def test_the_admin_shows_history_read_only(signed_in, clock):
    kept = entry(clock.now)
    changelist = reverse("admin:core_historyentry_changelist")

    assert "HDFC" in signed_in.get(changelist).text
    add = reverse("admin:core_historyentry_add")
    assert signed_in.get(add).status_code == 403
    change = reverse("admin:core_historyentry_change", args=[kept.pk])
    assert signed_in.post(change, {"subject_name": "ICICI"}).status_code == 403
    delete = reverse("admin:core_historyentry_delete", args=[kept.pk])
    assert signed_in.post(delete, {"post": "yes"}).status_code == 403
    signed_in.post(
        changelist, {"action": "delete_selected", "_selected_action": [kept.pk]}
    )
    assert list(HistoryEntry.objects.values_list("subject_name", flat=True)) == ["HDFC"]


@pytest.mark.django_db
def test_the_base_currency_isnt_changed_unless_its_history_is(signed_in, monkeypatch):
    def fail(*args, **kwargs):
        raise DatabaseError

    monkeypatch.setattr(HistoryEntry.objects, "create", fail)

    with pytest.raises(DatabaseError):
        signed_in.post(reverse("base_currency"), {"base_currency": "USD"})

    assert Setting.load().base_currency == "INR"


@pytest.mark.django_db
def test_it_needs_signing_in(client):
    response = client.get(HISTORY)

    assert response["Location"].startswith(reverse("sign_in"))
