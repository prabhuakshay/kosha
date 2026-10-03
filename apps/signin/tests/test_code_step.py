import pytest
from django.urls import reverse
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.signin.testing import authenticator_code, enter_code, sign_in


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_password_alone_does_not_reach_the_admin(client):
    admin = reverse("admin:index")
    sign_in(client)

    assert client.get(admin)["Location"] == f"{reverse('code_step')}?next={admin}"


@pytest.mark.django_db
def test_owner_with_no_way_to_sign_in_is_sent_to_set_one_up(client, owner):
    sign_in(client)

    home = reverse("home")
    assert client.get(home)["Location"] == f"{reverse('choose_way')}?next={home}"


@pytest.mark.django_db
def test_right_authenticator_code_finishes_signing_in(client, authenticator):
    admin = reverse("admin:index")
    sign_in(client)

    response = enter_code(client, authenticator_code(authenticator.bin_key), admin)

    assert response["Location"] == admin
    assert client.get(reverse("home")).status_code == 200


@pytest.mark.django_db
def test_wrong_code_does_not_finish_signing_in(client, authenticator):
    sign_in(client)

    response = enter_code(client, "000000")

    assert response.status_code == 200
    assert "That code doesn&#x27;t match. Try the one showing now." in response.text
    assert client.get(reverse("home")).status_code == 302


@pytest.fixture
def recovery_code(owner):
    StaticDevice.objects.create(user=owner, name="Recovery codes").token_set.create(
        token="k7m2x9qa"
    )
    return "K7M2 X9QA"


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_recovery_code_finishes_signing_in_once(client, recovery_code):
    sign_in(client)

    enter_code(client, recovery_code)

    assert client.get(reverse("home")).status_code == 200
    client.post(reverse("sign_out"))
    sign_in(client)
    response = enter_code(client, recovery_code)
    assert "That code doesn&#x27;t match." in response.text
    assert client.get(reverse("home")).status_code == 302


@pytest.mark.django_db
def test_password_alone_cannot_replace_the_authenticator_app(client, authenticator):
    sign_in(client)

    for name in ("choose_way", "set_up_authenticator"):
        response = client.get(reverse(name))
        assert response["Location"] == reverse("home"), name
    response = client.post(reverse("set_up_authenticator"), {"code": "000000"})
    assert response["Location"] == reverse("home")
    assert list(TOTPDevice.objects.all()) == [authenticator]


@pytest.mark.django_db
def test_code_step_without_a_way_to_sign_in_goes_to_set_one_up(client, owner):
    sign_in(client)

    assert client.get(reverse("code_step"))["Location"] == reverse("choose_way")


@pytest.mark.django_db
@pytest.mark.usefixtures("authenticator")
def test_sign_out_from_the_code_step(client):
    sign_in(client)

    client.post(reverse("sign_out"))

    assert client.get(reverse("code_step"))["Location"].startswith(reverse("sign_in"))
