"""Forms for Masters."""

from decimal import Decimal
from typing import TYPE_CHECKING

from django import forms
from django.utils import timezone

from apps.core.money import base_currency, decimal_places
from apps.masters.models import KINDS, Account

if TYPE_CHECKING:
    from datetime import date


CLASH_NOUN = {
    Account.Type.ASSET: "an Asset account",
    Account.Type.LIABILITY: "a Liability",
    Account.Type.EXPENSE: "an Expense account",
    Account.Type.INCOME: "an Income account",
}


class AccountForm(forms.ModelForm):
    """An Account's name and notes, all an Expense or Income account has."""

    class Meta:
        model = Account
        fields = ["name", "notes"]

    def clean_name(self) -> str:
        """Refuse a name another Account of the same type has, ignoring case.

        Returns:
            The name.

        Raises:
            ValidationError: Another Account of the same type has it.
        """
        name = self.cleaned_data["name"]
        clash = (
            Account.objects.filter(type=self.instance.type, name__iexact=name)
            .exclude(pk=self.instance.pk)
            .first()
        )
        if clash:
            noun = CLASH_NOUN[self.instance.type]
            msg = f"There's already {noun} called “{clash.name}”."
            raise forms.ValidationError(msg)
        return name


class BalanceAccountForm(AccountForm):
    """An Asset account's or Liability's name, Kind, Opening balance and more.

    Only Kinds of the Account's own type are offered or accepted.
    """

    # Places are checked against the Base currency, not the column's four.
    opening_balance = forms.DecimalField(max_digits=24, initial=Decimal(0))

    class Meta:
        model = Account
        fields = ["name", "kind", "opening_balance", "opened_on", "notes"]

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.fields["kind"].choices = [
            (kind.value, kind.label) for kind in KINDS[self.instance.type]
        ]
        self.fields["kind"].required = True
        self.fields["opened_on"].required = True
        if self.instance.pk:
            self.initial["opening_balance"] = in_places(self.instance.opening_balance)
        else:
            self.initial["opened_on"] = timezone.localdate()

    def clean_opening_balance(self) -> Decimal:
        """Hold the Opening balance to the currency's places, and a Closed one at 0.

        Returns:
            The Opening balance.

        Raises:
            ValidationError: It has more decimal places than the currency, or
                the Account is Closed and it isn't zero.
        """
        amount = self.cleaned_data["opening_balance"]
        places = decimal_places()
        if -amount.normalize().as_tuple().exponent > places:
            msg = (
                f"Amounts in {base_currency()} have no decimal places."
                if places == 0
                else f"Amounts in {base_currency()} have at most {places} decimal "
                "places."
            )
            raise forms.ValidationError(msg)
        if self.instance.closed and amount:
            msg = "A closed account's balance must stay zero. Reopen it first."
            raise forms.ValidationError(msg)
        return amount

    def clean_opened_on(self) -> date:
        """Refuse an opening date in the future.

        Returns:
            The opening date.

        Raises:
            ValidationError: It's after today.
        """
        opened_on = self.cleaned_data["opened_on"]
        if opened_on > timezone.localdate():
            msg = "The opening date can't be in the future."
            raise forms.ValidationError(msg)
        return opened_on


def in_places(amount: Decimal) -> Decimal:
    """Show a stored amount to the Base currency's places, not the column's.

    Args:
        amount: The amount, as stored.

    Returns:
        The amount to the currency's places, unless that would lose some of it.
    """
    exact = amount.quantize(Decimal(1).scaleb(-decimal_places()))
    return exact if exact == amount else amount.normalize()
