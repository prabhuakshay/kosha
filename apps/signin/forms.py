"""Forms for Claiming the install and signing in."""

from typing import TYPE_CHECKING

from django import forms
from django.contrib.auth import get_user_model, password_validation

from apps.signin import ways
from apps.signin.claim import is_setup_code

if TYPE_CHECKING:
    from django_otp.models import Device
    from django_otp.plugins.otp_totp.models import TOTPDevice

    from apps.users.models import User

WRONG_CODE = "That code doesn't match. Try the one showing now."


class SetupCodeForm(forms.Form):
    """The code printed in the server's log."""

    code = forms.CharField(max_length=32)

    def clean_code(self) -> str:
        """Refuse anything but this install's Setup code.

        Returns:
            The code as entered.

        Raises:
            ValidationError: The code is wrong.
        """
        code = self.cleaned_data["code"]
        if not is_setup_code(code):
            msg = "That isn't the Setup code. Check the server's log."
            raise forms.ValidationError(msg)
        return code


class OwnerForm(forms.Form):
    """The Owner's name, email and password."""

    name = forms.CharField(max_length=255)
    email = forms.EmailField(max_length=254)
    password = forms.CharField(strip=False)

    def clean(self) -> dict:
        """Hold the password to Kosha's password rules, name and email included.

        Returns:
            The cleaned data.
        """
        cleaned = super().clean()
        if "password" in cleaned:
            owner = get_user_model()(
                name=cleaned.get("name", ""), email=cleaned.get("email", "")
            )
            try:
                password_validation.validate_password(cleaned["password"], owner)
            except forms.ValidationError as error:
                self.add_error("password", error)
        return cleaned

    def save(self) -> User:
        """Create the Owner, who has the admin too.

        Returns:
            The Owner.
        """
        return get_user_model().objects.create_superuser(
            self.cleaned_data["email"],
            self.cleaned_data["password"],
            name=self.cleaned_data["name"],
        )


class NewAuthenticatorForm(forms.Form):
    """A code from the Authenticator app being set up, which saves it.

    Args:
        device: The unsaved device being set up.
    """

    code = forms.CharField(max_length=32)

    def __init__(self, device: TOTPDevice, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.device = device

    def clean_code(self) -> str:
        """Save the device if the app shows a right code.

        Returns:
            The code as entered.

        Raises:
            ValidationError: The code is wrong.
        """
        code = self.cleaned_data["code"]
        if not ways.confirm_authenticator(self.device, code):
            raise forms.ValidationError(WRONG_CODE)
        return code


class CodeForm(forms.Form):
    """A code from the Authenticator app, or a Recovery code.

    Args:
        owner: Whose codes to check.
        recovery: Whether a Recovery code may stand in for the app's code.
    """

    code = forms.CharField(max_length=32)

    def __init__(
        self, owner: User, *args: object, recovery: bool = True, **kwargs: object
    ) -> None:
        super().__init__(*args, **kwargs)
        self.owner = owner
        self.recovery = recovery
        self.device: Device | None = None

    def clean_code(self) -> str:
        """Match the code, keeping the device it matched.

        Returns:
            The code as entered.

        Raises:
            ValidationError: It matches nothing.
        """
        code = self.cleaned_data["code"]
        self.device = ways.matching_device(self.owner, code, recovery=self.recovery)
        if self.device is None:
            raise forms.ValidationError(WRONG_CODE)
        return code
