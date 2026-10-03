import re

import pytest
from django.urls import reverse

from apps.core.testing import sub_links, tags
from apps.masters.models import Account

MASTERS = reverse("masters:masters")


@pytest.mark.django_db
def test_the_rail_and_tab_bar_lead_to_masters(signed_in):
    response = signed_in.get(reverse("home"))

    masters = tags(response, "a", href=MASTERS)
    assert {m["class"] for m in masters} == {"rail-link rail-wide", "tab"}
    assert 'rail-label">Accounts<' not in response.text


LISTS = ["assets", "liabilities", "income", "expenses", "categories", "tags"]


@pytest.mark.django_db
def test_the_wide_rail_shows_the_lists_only_while_in_masters(signed_in):
    inside = signed_in.get(reverse("masters:assets"))
    outside = signed_in.get(reverse("home"))

    assert sub_links(inside, 'class="rail-sub"') == [
        reverse(f"masters:{n}") for n in LISTS
    ]
    assert 'class="rail-sub"' not in outside.text


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["home", "masters:assets"])
def test_the_icon_rail_opens_the_lists_in_a_flyout(signed_in, name):
    response = signed_in.get(reverse(name))

    assert tags(response, "button", popovertarget="masters-flyout")
    assert "popover" in tags(response, "div", id="masters-flyout")[0]
    assert sub_links(response, 'id="masters-flyout"') == [
        reverse(f"masters:{n}") for n in LISTS
    ]


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["masters:masters", *(f"masters:{n}" for n in LISTS)])
def test_the_masters_tab_is_current_anywhere_in_masters(signed_in, name):
    response = signed_in.get(reverse(name))

    assert tags(response, "a", href=MASTERS, **{"class": "tab", "aria-current": "page"})


@pytest.mark.django_db
@pytest.mark.parametrize("name", LISTS)
def test_the_list_open_is_marked_current(signed_in, name):
    response = signed_in.get(reverse(f"masters:{name}"))

    current = tags(response, "a", **{"class": "sub-link", "aria-current": "page"})
    assert {c["href"] for c in current} == {reverse(f"masters:{name}")}


def row_subs(response):
    return dict(
        re.findall(
            r'<span class="block text-\[15px\] font-semibold">([^<]+)</span>\s*'
            r'<span class="row-sub">([^<]+)</span>',
            response.text,
        )
    )


@pytest.mark.django_db
def test_the_index_lists_every_list_with_counts_and_totals(signed_in):
    Account.objects.create(
        type=Account.Type.ASSET, kind="bank", name="HDFC", opening_balance=300000
    )
    Account.objects.create(
        type=Account.Type.ASSET, kind="cash", name="Wallet", opening_balance=20000
    )

    response = signed_in.get(MASTERS)

    for name in LISTS:
        assert tags(response, "a", href=reverse(f"masters:{name}"), **{"class": "row"})
    assert row_subs(response) == {
        "Assets": "2 · ₹3,20,000.00",
        "Liabilities": "None yet",
        "Income": "None yet",
        "Expenses": "None yet",
        "Categories": "None yet",
        "Tags": "None yet",
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("name", "says"),
    [
        ("liabilities", "credit cards, loans, a mortgage"),
        ("income", "who pays you"),
        ("expenses", "who you pay"),
        ("categories", "What money is spent or received for"),
        ("tags", "The context money moves in"),
        ("assets", "bank accounts, deposits, cash and investments"),
    ],
)
def test_an_empty_list_says_what_belongs_there(signed_in, name, says):
    response = signed_in.get(reverse(f"masters:{name}"))

    assert "yet</h1>" in response.text
    assert says in response.text


@pytest.mark.django_db
def test_an_empty_assets_list_offers_the_first_one(signed_in):
    response = signed_in.get(reverse("masters:assets"))

    assert tags(response, "a", href=reverse("masters:new_asset"), **{"class": "btn"})


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    [
        MASTERS,
        *(reverse(f"masters:{n}") for n in LISTS),
        reverse("masters:new_asset"),
        reverse("masters:asset", args=[1]),
        reverse("masters:edit_asset", args=[1]),
    ],
)
def test_every_masters_page_needs_signing_in(client, path):
    response = client.get(path)

    assert response["Location"].startswith(reverse("sign_in"))
