import re
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

from apps.core.testing import tags
from apps.masters.models import Category
from apps.masters.testing import category, errors, history
from apps.masters.testing import category_url as url

CATEGORIES = reverse("masters:categories")
NEW = reverse("masters:new_category")
PALETTE = [
    "forest",
    "sage",
    "teal",
    "sky",
    "indigo",
    "plum",
    "rose",
    "rust",
    "ochre",
    "olive",
    "earth",
    "stone",
]


def add(client, **fields):
    data = {"name": "Groceries", "color": "sage", "icon": "shopping-cart"} | fields
    return client.post(NEW, data)


def edit(client, of, **fields):
    data = {"name": of.name, "color": of.color, "icon": of.icon} | fields
    return client.post(url("edit_", of), data)


def checked(response, name):
    return [
        t["value"]
        for t in tags(response, "input", type="radio", name=name)
        if "checked" in t
    ]


@pytest.mark.django_db
def test_a_fresh_install_has_none_and_says_how_to_add_the_first(signed_in):
    response = signed_in.get(CATEGORIES)

    assert not Category.objects.exists()
    assert "No categories yet</h1>" in response.text
    assert "What money is spent or received for" in response.text
    assert tags(response, "a", href=NEW, **{"class": "btn"})


@pytest.mark.django_db
def test_the_owner_adds_one_and_sees_it(signed_in):
    response = add(signed_in, name="Groceries", color="sage", icon="shopping-cart")

    created = Category.objects.get()
    assert (created.name, created.color, created.icon) == (
        "Groceries",
        "sage",
        "shopping-cart",
    )
    assert response["Location"] == url("", created)
    page = signed_in.get(response["Location"])
    assert '<h1 class="display page-title">Groceries</h1>' in page.text
    assert "<dd data-color-name>Sage</dd>" in page.text
    assert "data-icon-name>Shopping cart</dd>" in page.text
    assert tags(page, "i", **{"data-lucide": "shopping-cart"})


@pytest.mark.django_db
def test_one_needs_no_icon(signed_in):
    response = add(signed_in, icon="")

    created = Category.objects.get()
    assert not created.icon
    page = signed_in.get(response["Location"])
    assert "data-icon-name>None</dd>" in page.text


@pytest.mark.django_db
def test_the_form_offers_the_whole_palette_and_the_curated_icons(signed_in):
    response = signed_in.get(NEW)

    colors = tags(response, "input", type="radio", name="color")
    icons = tags(response, "input", type="radio", name="icon")
    assert [c["value"] for c in colors] == PALETTE
    assert not icons[0]["value"]
    assert 30 <= len(icons) - 1 <= 50
    assert all(tags(response, "i", **{"data-lucide": i["value"]}) for i in icons[1:])


@pytest.mark.django_db
def test_a_fresh_install_offers_the_first_color_and_no_icon(signed_in):
    response = signed_in.get(NEW)

    assert checked(response, "color") == ["forest"]
    assert checked(response, "icon") == [""]


@pytest.mark.django_db
def test_the_form_offers_the_least_used_color(signed_in):
    for color in ["forest", "forest", "sage", "teal"]:
        category(f"In {color} {Category.objects.count()}", color)

    response = signed_in.get(NEW)

    assert checked(response, "color") == ["sky"]


@pytest.mark.django_db
def test_a_new_one_without_a_color_gets_the_least_used(signed_in):
    for i, color in enumerate(PALETTE):
        category(f"Once {i}", color)
    category("Twice forest", "forest")
    category("Twice sage", "sage")

    add(signed_in, name="Rent", color="")

    assert Category.objects.get(name="Rent").color == "teal"


@pytest.mark.django_db
def test_closed_ones_count_towards_the_least_used_color(signed_in):
    category("Old", "forest", closed=True)

    add(signed_in, name="Rent", color="")

    assert Category.objects.get(name="Rent").color == "sage"


@pytest.mark.django_db
@pytest.mark.parametrize("color", ["red", "#ff0000", "FOREST"])
def test_only_palette_colors_are_accepted(signed_in, color):
    response = add(signed_in, color=color)

    assert response.status_code == 200
    assert errors(response)
    assert not Category.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("icon", ["skull", "bomb", "Shopping-cart"])
def test_only_curated_icons_are_accepted(signed_in, icon):
    response = add(signed_in, icon=icon)

    assert response.status_code == 200
    assert errors(response)
    assert not Category.objects.exists()


@pytest.mark.django_db
def test_an_edit_keeps_to_the_palette(signed_in):
    groceries = category()

    response = edit(signed_in, groceries, color="#00ff00")

    assert errors(response)
    groceries.refresh_from_db()
    assert groceries.color == "forest"


@pytest.mark.django_db
def test_two_cant_share_a_name_ignoring_case(signed_in):
    add(signed_in, name="Groceries")

    response = add(signed_in, name="GROCERIES")

    assert errors(response) == ["There's already a Category called “Groceries”."]
    assert Category.objects.count() == 1


@pytest.mark.django_db
def test_the_owner_edits_one(signed_in):
    groceries = category()

    response = edit(signed_in, groceries, name="Food", color="rose", icon="utensils")

    assert response["Location"] == url("", groceries)
    groceries.refresh_from_db()
    assert (groceries.name, groceries.color, groceries.icon) == (
        "Food",
        "rose",
        "utensils",
    )


@pytest.mark.django_db
def test_the_edit_form_shows_its_own_color_and_icon(signed_in):
    category("Rent", "forest")
    groceries = category(color="rose", icon="utensils")

    response = signed_in.get(url("edit_", groceries))

    assert checked(response, "color") == ["rose"]
    assert checked(response, "icon") == ["utensils"]


@pytest.mark.django_db
def test_an_edit_cant_take_another_ones_name(signed_in):
    groceries = category()
    category("Rent")

    response = edit(signed_in, groceries, name="rent")

    assert errors(response) == ["There's already a Category called “Rent”."]


@pytest.mark.django_db
def test_they_are_listed_alphabetically_with_their_color_and_icon(signed_in):
    category("Rent", "sky", "house")
    category("groceries", "sage", "shopping-cart")
    category("Fuel", "rust")

    response = signed_in.get(CATEGORIES)

    rows = re.findall(
        r'class="row"[^>]*>\s*<span class="tile category-tile color-(\w+)">'
        r'(?:<i data-lucide="([\w-]+)"></i>)?<span class="category-dot"></span>'
        r"</span>\s*"
        r'<span class="min-w-0 flex-1 truncate text-\[15px\] font-semibold">([^<]+)<',
        response.text,
    )
    assert rows == [
        ("rust", "", "Fuel"),
        ("sage", "shopping-cart", "groceries"),
        ("sky", "house", "Rent"),
    ]


@pytest.mark.django_db
def test_creating_and_editing_one_is_in_its_history(signed_in):
    add(signed_in, name="Groceries", color="sage", icon="shopping-cart")
    groceries = Category.objects.get()
    edit(signed_in, groceries, name="Food", color="rose", icon="")

    assert history(signed_in.get(url("", groceries))) == (
        ["Edited", "Created"],
        ["Name: Groceries → Food", "Color: Sage → Rose", "Icon: Shopping cart → None"],
    )


@pytest.mark.django_db
def test_saving_one_unchanged_adds_nothing(signed_in):
    groceries = category()

    edit(signed_in, groceries)

    assert history(signed_in.get(url("", groceries))) == ([], [])


@pytest.mark.django_db
def test_the_full_history_names_it_a_category(signed_in):
    add(signed_in, name="Groceries")

    response = signed_in.get(reverse("history"))

    assert "data-history-subject>Groceries · Category<" in response.text


def luminance(hex_):
    channels = [int(hex_[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = (
        c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels
    )
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def mix(color, background, share):
    """``color-mix(in srgb, color share, background)``, as a tile tints with it."""
    channels = [
        round(
            int(color[i : i + 2], 16) * share
            + int(background[i : i + 2], 16) * (1 - share)
        )
        for i in (1, 3, 5)
    ]
    return "#" + "".join(f"{c:02x}" for c in channels)


def contrast(a, b):
    light, dark = sorted([luminance(a), luminance(b)], reverse=True)
    return (light + 0.05) / (dark + 0.05)


def themes():
    """Each theme's color tokens, from the stylesheet the app is built from."""
    css = (Path(settings.BASE_DIR) / "assets/css/app.css").read_text()
    light = re.search(r":root \{(.*?)\}", css, re.DOTALL)[1]
    dark = re.search(r":root\.dark \{(.*?)\}", css, re.DOTALL)[1]
    return {
        name: dict(re.findall(r"--([\w-]+): (#[0-9a-f]{6});", block))
        for name, block in [("light", light), ("dark", dark)]
    }


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("color", PALETTE)
def test_each_palette_color_reads_well_in_both_themes(theme, color):
    tokens = themes()[theme]

    value = tokens[f"category-{color}"]
    tile = mix(value, tokens["surface"], 0.14)
    for background in [tokens["bg"], tokens["list"], tokens["surface"], tile]:
        assert contrast(value, background) >= 3


def test_the_dark_theme_is_the_same_chosen_or_automatic():
    css = (Path(settings.BASE_DIR) / "assets/css/app.css").read_text()
    automatic = re.search(r":root:not\(\.light\) \{(.*?)\}", css, re.DOTALL)[1]
    chosen = re.search(r":root\.dark \{(.*?)\}", css, re.DOTALL)[1]

    assert automatic.split() == chosen.split()
