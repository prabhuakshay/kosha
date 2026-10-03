"""Forms for Claiming the install."""

from typing import TYPE_CHECKING

from django import forms
from django.contrib.auth import get_user_model, password_validation

from apps.signin.claim import is_setup_code

if TYPE_CHECKING:
    from apps.users.models import User


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
