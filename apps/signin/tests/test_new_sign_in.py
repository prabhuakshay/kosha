from smtplib import SMTPException

import pytest
from django.core import mail
from django.core.mail.backends.locmem import EmailBackend
from django.urls import reverse

from apps.core.testing import EMAIL
from apps.signin.models import SecurityLogEntry
from apps.signin.testing import (
    SAFARI_ON_IPHONE,
    add_passkey,
    browser_at,
    claim,
    sign_in,
    sign_in_fully,
    sign_in_with_passkey,
)


@pytest.fixture
def signed_in_before(authenticator):
    sign_in_fully(browser_at("198.51.100.7"), authenticator)
    mail.outbox.clear()


@pytest.mark.django_db
@pytest.mark.usefixtures("signed_in_before")
def test_a_sign_in_from_a_new_address_emails_the_owner(authenticator):
    sign_in_fully(browser_at("203.0.113.5"), authenticator, 1)

    (email,) = mail.outbox
    assert email.to == [EMAIL]
    assert email.subject == "New sign-in to Kosha"
    assert "Device: Chrome on macOS" in email.body
    assert "Address: 203.0.113.5" in email.body
    assert "How: Password and authenticator code" in email.body
    assert f"http://testserver{reverse('sessions')}" in email.body


@pytest.mark.django_db
@pytest.mark.usefixtures("signed_in_before")
def test_a_sign_in_from_a_new_device_emails_the_owner(authenticator):
    sign_in_fully(browser_at("198.51.100.7", SAFARI_ON_IPHONE), authenticator, 1)

    (email,) = mail.outbox
    assert "Device: Safari on iPhone" in email.body


@pytest.mark.django_db
@pytest.mark.usefixtures("signed_in_before")
def test_a_sign_in_from_a_known_address_and_device_sends_nothing(authenticator):
    sign_in_fully(browser_at("198.51.100.7"), authenticator, 1)

    assert mail.outbox == []


@pytest.mark.django_db
@pytest.mark.usefixtures("signed_in_before", "browser")
def test_a_passkey_sign_in_from_somewhere_new_emails_the_owner(owner):
    add_passkey(owner)

    sign_in_with_passkey(browser_at("203.0.113.5"))

    (email,) = mail.outbox
    assert "How: Passkey" in email.body


@pytest.mark.django_db
@pytest.mark.usefixtures("signed_in_before")
def test_the_password_alone_sends_nothing():
    sign_in(browser_at("203.0.113.5"))

    assert mail.outbox == []


@pytest.mark.django_db
def test_claiming_kosha_sends_nothing(client):
    claim(client)

    assert mail.outbox == []


@pytest.mark.django_db
@pytest.mark.usefixtures("signed_in_before")
def test_a_failed_send_doesnt_stop_the_sign_in(authenticator, monkeypatch, caplog):
    def fail(*args, **kwargs):
        raise SMTPException

    monkeypatch.setattr(EmailBackend, "send_messages", fail)
    client = browser_at("203.0.113.5")

    response = sign_in_fully(client, authenticator, 1)

    assert response["Location"] == reverse("home")
    assert client.get(reverse("home")).status_code == 200
    assert SecurityLogEntry.objects.filter(address="203.0.113.5").exists()
    assert "new sign-in" in caplog.text
