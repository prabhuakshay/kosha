import pytest
from django.urls import reverse

from apps.core.testing import tags

BASE_CURRENCY = reverse("base_currency")


def chosen(response):
    return [o["value"] for o in tags(response, "option") if "selected" in o]


@pytest.mark.django_db
def test_a_fresh_install_is_in_inr(signed_in):
    response = signed_in.get(BASE_CURRENCY)

    assert chosen(response) == ["INR"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("currency", "written"),
    [("INR", "₹3,20,000.00"), ("USD", "$320,000.00"), ("JPY", "¥320,000")],
)
def test_the_owner_changes_it_and_sees_amounts_written_its_way(
    signed_in, currency, written
):
    response = signed_in.post(BASE_CURRENCY, {"base_currency": currency}, follow=True)

    assert chosen(response) == [currency]
    assert f"data-sample>{written}</p>" in response.text


@pytest.mark.django_db
def test_it_warns_that_amounts_are_relabelled_not_converted(signed_in):
    response = signed_in.get(BASE_CURRENCY)

    assert "relabels every amount" in response.text
    assert "Nothing is converted." in response.text


@pytest.mark.django_db
def test_only_a_currency_in_use_today_can_be_chosen(signed_in):
    response = signed_in.post(BASE_CURRENCY, {"base_currency": "DEM"})

    assert response.status_code == 200
    assert chosen(signed_in.get(BASE_CURRENCY)) == ["INR"]


@pytest.mark.django_db
def test_it_needs_signing_in(client):
    response = client.get(BASE_CURRENCY)

    assert response["Location"].startswith(reverse("sign_in"))
