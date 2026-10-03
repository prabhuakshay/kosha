import re
from io import StringIO

import pytest
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from apps.core.testing import EMAIL
from apps.signin.testing import (
    DETAILS,
    claim,
    enter_setup_code,
    printed_code,
    set_up_authenticator,
    sign_in,
)


@pytest.mark.django_db
def test_unclaimed_install_sends_sign_in_to_claim(client):
    response = client.get(reverse("sign_in"))

    assert response["Location"] == reverse("claim")


@pytest.mark.django_db
def test_claim_asks_for_the_setup_code(client):
    response = client.get(reverse("claim"))

    assert response.status_code == 200
    assert "Setup code" in response.text


@pytest.mark.django_db
def test_setup_code_is_twelve_digits_in_groups_of_four(client):
    assert re.fullmatch(r"\d{4} \d{4} \d{4}", printed_code())


@pytest.mark.django_db
def test_setup_code_stays_the_same(client):
    assert printed_code() == printed_code()


@pytest.mark.django_db
def test_claim_makes_the_owner_and_signs_them_in(client, django_user_model):
    response = claim(client)

    assert response["Location"] == reverse("choose_way")
    (owner,) = django_user_model.objects.all()
    assert owner.name == "Asha Rao"
    assert owner.email == EMAIL
    assert client.get(reverse("home"))["Location"].startswith(reverse("choose_way"))


@pytest.mark.django_db
def test_the_owner_has_the_admin(client):
    claim(client)
    set_up_authenticator(client)

    assert client.get(reverse("admin:index")).status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("spacing", ["", "-", "  "])
def test_setup_code_may_be_typed_with_any_spacing(client, spacing):
    code = printed_code().replace(" ", spacing)

    response = enter_setup_code(client, code)

    assert response["Location"] == reverse("claim_owner")


@pytest.mark.django_db
def test_wrong_setup_code_is_refused(client, django_user_model):
    right = printed_code()
    code = right[:-1] + str((int(right[-1]) + 1) % 10)

    response = enter_setup_code(client, code)

    assert response.status_code == 200
    assert "That isn&#x27;t the Setup code." in response.text
    assert client.get(reverse("claim_owner"))["Location"] == reverse("claim")
    assert client.post(reverse("claim_owner"), DETAILS)["Location"] == reverse("claim")
    assert not django_user_model.objects.exists()


@pytest.mark.django_db
def test_owner_details_need_the_setup_code_in_this_session(django_user_model):
    enter_setup_code(Client())
    other = Client()

    response = other.post(reverse("claim_owner"), DETAILS)

    assert response["Location"] == reverse("claim")
    assert not django_user_model.objects.exists()


@pytest.mark.django_db
def test_weak_password_is_refused(client, django_user_model):
    response = claim(client, password="password")

    assert response.status_code == 200
    assert "This password is too common." in response.text
    assert not django_user_model.objects.exists()


@pytest.mark.django_db
def test_password_like_the_name_or_email_is_refused(client, django_user_model):
    response = claim(client, name="Harbourlantern Q", password="harbourlantern")

    assert response.status_code == 200
    assert "too similar" in response.text
    assert not django_user_model.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "details",
    [{"name": ""}, {"email": "not an email"}, {"email": "a" * 250 + "@example.com"}],
)
def test_bad_owner_details_are_refused(client, django_user_model, details):
    response = claim(client, **details)

    assert response.status_code == 200
    assert not django_user_model.objects.exists()


@pytest.mark.django_db
def test_owner_signs_in_later_whatever_the_email_case(client):
    claim(client, email="Owner@Example.COM")
    client.post(reverse("sign_out"))

    sign_in(client)

    assert client.get(reverse("home"))["Location"].startswith(reverse("choose_way"))


@pytest.mark.django_db
def test_every_claim_route_goes_home_once_claimed(django_user_model):
    code = printed_code()
    midway = Client()
    enter_setup_code(midway, code)
    claim(Client())

    home = reverse("home")
    for client in (Client(), midway):
        assert client.get(reverse("claim"))["Location"] == home
        assert client.post(reverse("claim"), {"code": code})["Location"] == home
        assert client.get(reverse("claim_owner"))["Location"] == home
        assert client.post(reverse("claim_owner"), DETAILS)["Location"] == home
    assert django_user_model.objects.count() == 1


@pytest.mark.django_db
def test_no_setup_code_once_claimed(owner):
    out = StringIO()

    call_command("setup_code", stdout=out)

    assert "Setup code:" not in out.getvalue()
    assert "Kosha is claimed" in out.getvalue()
