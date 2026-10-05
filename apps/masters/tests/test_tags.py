import pytest
from django.urls import reverse

from apps.core.testing import tags
from apps.masters.models import Tag
from apps.masters.testing import errors, history, listed_at, tag
from apps.masters.testing import tag_url as url

TAGS = reverse("masters:tags")
NEW = reverse("masters:new_tag")


def add(client, name="Goa trip 2026"):
    return client.post(NEW, {"name": name})


def rename(client, of, name):
    return client.post(url("edit_", of), {"name": name})


@pytest.mark.django_db
def test_a_fresh_install_has_none_and_says_how_to_add_the_first(signed_in):
    response = signed_in.get(TAGS)

    assert "No tags yet</h1>" in response.text
    assert "The context money moves in" in response.text
    assert tags(response, "a", href=NEW, **{"class": "btn"})


@pytest.mark.django_db
def test_the_owner_adds_one_and_sees_it(signed_in):
    response = add(signed_in, "Goa trip 2026")

    created = Tag.objects.get()
    assert created.name == "Goa trip 2026"
    assert response["Location"] == url("", created)
    page = signed_in.get(response["Location"])
    assert "<h1>Goa trip 2026</h1>" in page.text
    assert tags(page, "a", href=url("", created), **{"aria-current": "page"})


@pytest.mark.django_db
def test_they_are_listed_alphabetically(signed_in):
    tag("reimbursable")
    tag("Goa trip 2026")
    tag("Diwali")

    assert listed_at(signed_in, TAGS) == (
        ["Diwali", "Goa trip 2026", "reimbursable"],
        [],
    )


@pytest.mark.django_db
def test_two_cant_share_a_name_ignoring_case(signed_in):
    add(signed_in, "Reimbursable")

    response = add(signed_in, "REIMBURSABLE")

    assert errors(response) == ["There's already a Tag called “Reimbursable”."]
    assert Tag.objects.count() == 1


@pytest.mark.django_db
def test_the_owner_renames_one(signed_in):
    goa = tag("Goa trp")

    response = rename(signed_in, goa, "Goa trip")

    assert response["Location"] == url("", goa)
    goa.refresh_from_db()
    assert goa.name == "Goa trip"


@pytest.mark.django_db
def test_a_rename_cant_take_another_ones_name(signed_in):
    goa = tag("Goa")
    tag("Diwali")

    response = rename(signed_in, goa, "diwali")

    assert errors(response) == ["There's already a Tag called “Diwali”."]
    goa.refresh_from_db()
    assert goa.name == "Goa"


@pytest.mark.django_db
def test_a_rename_can_change_only_the_case(signed_in):
    goa = tag("goa")

    rename(signed_in, goa, "Goa")

    goa.refresh_from_db()
    assert goa.name == "Goa"


@pytest.mark.django_db
def test_creating_and_renaming_one_is_in_its_history(signed_in):
    add(signed_in, "Goa trp")
    goa = Tag.objects.get()
    rename(signed_in, goa, "Goa trip")

    assert history(signed_in.get(url("", goa))) == (
        ["Edited", "Created"],
        ["Name: Goa trp → Goa trip"],
    )


@pytest.mark.django_db
def test_saving_one_unchanged_adds_nothing(signed_in):
    goa = tag()

    rename(signed_in, goa, goa.name)

    assert history(signed_in.get(url("", goa))) == ([], [])
