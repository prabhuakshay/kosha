import re

import pytest
from django.urls import reverse

from apps.core.testing import tags
from apps.masters.models import Account, Category, Tag

ACCOUNTS = reverse("masters:accounts")
LISTS = ["accounts", "categories", "tags"]


@pytest.mark.django_db
@pytest.mark.parametrize("name", LISTS)
def test_the_side_bar_leads_to_each_list(signed_in, name):
    response = signed_in.get(reverse("home"))

    assert tags(
        response, "a", href=reverse(f"masters:{name}"), **{"class": "side-link"}
    )


@pytest.mark.django_db
@pytest.mark.parametrize("name", LISTS)
def test_the_list_open_is_marked_current_in_the_side_bar(signed_in, name):
    response = signed_in.get(reverse(f"masters:{name}"))

    current = tags(response, "a", **{"class": "side-link", "aria-current": "page"})
    assert [c["href"] for c in current] == [reverse(f"masters:{name}")]


@pytest.mark.django_db
@pytest.mark.parametrize("name", LISTS)
def test_the_settings_tab_is_current_anywhere_in_the_lists(signed_in, name):
    response = signed_in.get(reverse(f"masters:{name}"))

    assert tags(
        response,
        "a",
        href=reverse("settings"),
        **{"class": "tab", "aria-current": "page"},
    )


@pytest.mark.django_db
@pytest.mark.parametrize("name", LISTS)
def test_each_list_goes_back_to_settings_on_phones(signed_in, name):
    response = signed_in.get(reverse(f"masters:{name}"))

    assert tags(
        response, "a", href=reverse("settings"), **{"aria-label": "Back to Settings"}
    )


@pytest.mark.django_db
def test_settings_lists_each_list_with_how_many_are_open(signed_in):
    Account.objects.create(type=Account.Type.ASSET, kind="bank", name="HDFC")
    Account.objects.create(type=Account.Type.EXPENSE, name="Amazon", closed=True)
    Category.objects.create(name="Groceries", color="forest")
    Tag.objects.create(name="goa")

    response = signed_in.get(reverse("settings"))

    values = dict(
        re.findall(
            r'class="row-title">([^<]+)</span>.*?<span class="row-value">([^<]+)<',
            response.text,
            re.DOTALL,
        )[:3]
    )
    assert values == {"Accounts": "1 open", "Categories": "1 open", "Tags": "1"}


@pytest.mark.django_db
def test_the_add_menu_offers_every_kind_of_thing(signed_in):
    response = signed_in.get(reverse("home"))

    menu = response.text[response.text.index('id="add-menu"') :]
    for name in [
        "new_asset",
        "new_liability",
        "new_expense_account",
        "new_income_account",
        "new_category",
        "new_tag",
    ]:
        assert f'href="{reverse(f"masters:{name}")}"' in menu


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("name", "says"),
    [
        ("liabilities", "Money you owe"),
        ("income", "Someone who pays you"),
        ("expenses", "Someone you pay"),
        ("assets", "Money you have, or something you own"),
    ],
)
def test_an_empty_section_says_what_belongs_there(signed_in, name, says):
    response = signed_in.get(ACCOUNTS)

    start = response.text.index(f'id="{name}"')
    assert says in response.text[start : start + 600]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("name", "says"),
    [
        ("categories", "What money is spent or received for"),
        ("tags", "The context money moves in"),
    ],
)
def test_an_empty_list_says_what_belongs_there(signed_in, name, says):
    response = signed_in.get(reverse(f"masters:{name}"))

    assert "yet</h1>" in response.text
    assert says in response.text


@pytest.mark.django_db
def test_no_accounts_offers_the_first_one(signed_in):
    response = signed_in.get(ACCOUNTS)

    assert tags(response, "a", href=reverse("masters:new_asset"), **{"class": "btn"})


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    [
        ACCOUNTS,
        reverse("masters:categories"),
        reverse("masters:tags"),
        reverse("masters:new_asset"),
        reverse("masters:asset", args=[1]),
        reverse("masters:edit_asset", args=[1]),
        reverse("masters:new_liability"),
        reverse("masters:liability", args=[1]),
        reverse("masters:edit_liability", args=[1]),
        reverse("masters:new_expense_account"),
        reverse("masters:expense_account", args=[1]),
        reverse("masters:edit_expense_account", args=[1]),
        reverse("masters:new_income_account"),
        reverse("masters:income_account", args=[1]),
        reverse("masters:edit_income_account", args=[1]),
    ],
)
def test_every_masters_page_needs_signing_in(client, path):
    response = client.get(path)

    assert response["Location"].startswith(reverse("sign_in"))
