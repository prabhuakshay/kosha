import re

import pytest
from django.urls import NoReverseMatch, reverse

from apps.core.testing import tags
from apps.masters.models import Tag
from apps.masters.testing import notices, tag
from apps.masters.testing import tag_url as url

TAGS = reverse("masters:tags")
NEW = reverse("masters:new_tag")


@pytest.mark.django_db
def test_an_unused_one_is_deleted(signed_in):
    goa = tag()

    response = signed_in.post(url("delete_", goa), follow=True)

    assert not Tag.objects.exists()
    assert response.redirect_chain[-1][0] == TAGS
    assert notices(response) == ["Deleted Goa trip 2026."]


@pytest.mark.django_db
def test_one_something_refers_to_cant_be_deleted(signed_in, monkeypatch):
    goa = tag()
    monkeypatch.setattr(Tag, "in_use", property(lambda _: True))

    response = signed_in.post(url("delete_", goa), follow=True)

    assert Tag.objects.get() == goa
    assert notices(response) == [
        "Goa trip 2026 can't be deleted while anything refers to it."
    ]
    assert not tags(response, "form", action=url("delete_", goa))


@pytest.mark.django_db
def test_delete_asks_first(signed_in):
    goa = tag()

    response = signed_in.get(url("", goa))

    form = re.search(
        rf'<form [^>]*action="{url("delete_", goa)}".*?</form>',
        response.text,
        re.DOTALL,
    )
    sheet = re.search(
        r'popovertarget="([\w-]+)" popovertargetaction="hide"[^>]*autofocus', form[0]
    )[1]
    assert "popover" in tags(response, "div", id=sheet)[0]
    assert tags(response, "button", popovertarget=sheet, type="button")


@pytest.mark.django_db
def test_one_cant_be_closed(signed_in):
    goa = tag()

    detail = signed_in.get(url("", goa))
    listing = signed_in.get(TAGS)

    assert not tags(detail, "i", **{"data-lucide": "archive"})
    assert "data-closed" not in detail.text
    assert not tags(listing, "details")
    for action in ["close_", "reopen_"]:
        with pytest.raises(NoReverseMatch):
            url(action, goa)


@pytest.mark.django_db
def test_a_deleted_one_stays_in_the_full_history(signed_in):
    signed_in.post(NEW, {"name": "Goa trp"})
    goa = Tag.objects.get()
    signed_in.post(url("edit_", goa), {"name": "Goa trip"})
    signed_in.post(url("delete_", goa))

    response = signed_in.get(reverse("history"))

    assert re.findall(r"data-history-action>([^<]+)<", response.text) == [
        "Deleted",
        "Edited",
        "Created",
    ]
    assert re.findall(r"data-history-subject>([^<]+)<", response.text) == [
        "Goa trip · Tag",
        "Goa trip · Tag",
        "Goa trp · Tag",
    ]


@pytest.mark.django_db
def test_the_index_counts_them(signed_in):
    settings = reverse("settings")

    def value():
        return re.search(
            r'>Tags</span>.*?<span class="row-value">([^<]+)<',
            signed_in.get(settings).text,
            re.DOTALL,
        )[1]

    assert value() == "None yet"
    tag("Goa")
    tag("Diwali")
    assert value() == "2"


@pytest.mark.django_db
@pytest.mark.parametrize("page", ["", "edit_"])
def test_the_one_open_is_marked_current(signed_in, page):
    goa = tag()

    response = signed_in.get(url(page, goa))

    current = [c for c in tags(response, "a") if c.get("aria-current")]
    assert {c["href"] for c in current if c["class"] in {"row", "side-link"}} == {
        url("", goa),
        TAGS,
    }


@pytest.mark.django_db
def test_one_goes_back_to_its_list(signed_in):
    goa = tag()

    response = signed_in.get(url("", goa))

    assert tags(response, "a", href=TAGS, **{"aria-label": "Back to Tags"})


@pytest.mark.django_db
def test_delete_needs_a_post(signed_in):
    goa = tag()

    assert signed_in.get(url("delete_", goa)).status_code == 405


@pytest.mark.django_db
@pytest.mark.parametrize("page", ["", "edit_"])
def test_every_page_needs_signing_in(client, page):
    goa = tag()

    for response in [client.get(NEW), client.get(url(page, goa))]:
        assert response["Location"].startswith(reverse("sign_in"))


@pytest.mark.django_db
def test_delete_needs_signing_in(client):
    goa = tag()

    response = client.post(url("delete_", goa))

    assert response["Location"].startswith(reverse("sign_in"))
    assert Tag.objects.get() == goa
