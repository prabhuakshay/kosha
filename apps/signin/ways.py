"""Ways to sign in, and the Recovery codes that stand in for one.

The Owner signs in with a Passkey alone, or with their password and a code from
the Authenticator app, or a Recovery code when the app is lost.
"""

import time
from base64 import b32encode
from typing import TYPE_CHECKING

import qrcode
from django.utils.safestring import SafeString, mark_safe
from django_otp.oath import TOTP
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp_webauthn.models import WebAuthnCredential
from qrcode.image.svg import SvgPathImage

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django_otp.models import Device

    from apps.users.models import User

RECOVERY_CODES = 10
AUTHENTICATOR_DIGITS = 6


def authenticator(owner: User) -> TOTPDevice | None:
    """The Owner's Authenticator app, if one is set up.

    Args:
        owner: Whose app to look for.

    Returns:
        The device, or None.
    """
    return TOTPDevice.objects.filter(user=owner, confirmed=True).first()


def has_way_to_sign_in(owner: User) -> bool:
    """Whether the Owner can finish a sign-in after their password.

    Recovery codes don't count: they stand in for a Way to sign in, but aren't one.

    Args:
        owner: Whose Ways to look for.

    Returns:
        True once one is set up.
    """
    return authenticator(owner) is not None or has_passkey(owner)


def has_passkey(owner: User) -> bool:
    """Whether the Owner has a Passkey.

    Args:
        owner: Whose Passkeys to look for.

    Returns:
        True once one is added.
    """
    return passkeys(owner).exists()


def passkeys(owner: User) -> QuerySet[WebAuthnCredential]:
    """The Owner's Passkeys.

    Args:
        owner: Whose Passkeys to list.

    Returns:
        The Passkeys.
    """
    return WebAuthnCredential.objects.filter(user=owner, confirmed=True)


def matching_device(owner: User, code: str, *, recovery: bool = True) -> Device | None:
    """Check a typed code against the Authenticator app and the Recovery codes.

    A Recovery code is used up by matching.

    Args:
        owner: Whose devices to check.
        code: What was typed; case, spaces and dashes are ignored.
        recovery: Whether a Recovery code may match.

    Returns:
        The device the code matched, or None.
    """
    code = "".join(c for c in code.lower() if c.isalnum())
    if code.isdigit() and len(code) == AUTHENTICATOR_DIGITS:
        device = authenticator(owner)
    elif recovery:
        device = StaticDevice.objects.filter(user=owner).first()
    else:
        device = None
    return device if device and device.verify_token(code) else None


def new_authenticator(owner: User, key: str) -> TOTPDevice:
    """An unsaved Authenticator app for the key the Owner is scanning.

    Args:
        owner: Whose it will be.
        key: The key, in hex.

    Returns:
        The device, not yet saved.
    """
    return TOTPDevice(user=owner, key=key, name="Authenticator app")


def qr_code(device: TOTPDevice) -> SafeString:
    """Draw the QR code an Authenticator app scans to add the device.

    Args:
        device: The device being set up.

    Returns:
        An SVG.
    """
    image = qrcode.make(device.config_url, image_factory=SvgPathImage, border=0)
    # Built from the key alone; nothing anyone typed goes into it.
    return mark_safe(image.to_string(encoding="unicode"))  # ruff: ignore[suspicious-mark-safe-usage]


def typed_key(device: TOTPDevice) -> str:
    """The key to type when the QR code can't be scanned.

    Args:
        device: The device being set up.

    Returns:
        The key in base32, in groups of four.
    """
    key = b32encode(device.bin_key).decode()
    return " ".join(key[i : i + 4] for i in range(0, len(key), 4))


def confirm_authenticator(device: TOTPDevice, code: str) -> bool:
    """Save a new Authenticator app once it shows a right code, replacing any old one.

    The code is checked by hand rather than with ``verify_token``, which would
    save the device on a wrong code too.

    Args:
        device: The unsaved device being set up.
        code: What the app showed.

    Returns:
        Whether the code was right and the device saved.
    """
    totp = TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift)
    totp.time = time.time()
    digits = "".join(c for c in code if c.isdigit())
    if not digits or not totp.verify(int(digits), device.tolerance):
        return False
    # The code just used can't be used again to sign in.
    device.last_t = totp.t()
    TOTPDevice.objects.filter(user=device.user).delete()
    device.save()
    return True


def has_recovery_codes(owner: User) -> bool:
    """Whether Recovery codes were ever issued, used up or not.

    Args:
        owner: Whose codes to look for.

    Returns:
        True once they have been.
    """
    return StaticDevice.objects.filter(user=owner).exists()


def recovery_codes_left(owner: User) -> int:
    """Count the Recovery codes not yet used.

    Args:
        owner: Whose codes to count.

    Returns:
        How many are left.
    """
    return StaticToken.objects.filter(device__user=owner).count()


def issue_recovery_codes(owner: User) -> list[str]:
    """Replace every Recovery code with a new set.

    Args:
        owner: Whose codes to replace.

    Returns:
        The new codes, to be shown once.
    """
    device, _ = StaticDevice.objects.get_or_create(
        user=owner, defaults={"name": "Recovery codes"}
    )
    device.token_set.all().delete()
    codes = [StaticToken.random_token() for _ in range(RECOVERY_CODES)]
    StaticToken.objects.bulk_create(
        StaticToken(device=device, token=code) for code in codes
    )
    return codes
