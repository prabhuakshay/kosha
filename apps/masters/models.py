"""Accounts: where money is, and who it goes to and comes from."""

from decimal import Decimal

from django.db import models
from django.db.models.functions import Lower


class Account(models.Model):
    """An Asset account, Liability, Expense account or Income account."""

    class Type(models.TextChoices):
        ASSET = "asset", "Asset account"
        LIABILITY = "liability", "Liability"
        EXPENSE = "expense", "Expense account"
        INCOME = "income", "Income account"

    class Kind(models.TextChoices):
        BANK = "bank", "Bank"
        DEPOSIT = "deposit", "Deposit"
        CASH = "cash", "Cash"
        INVESTMENT = "investment", "Investment"
        LENT = "lent", "Lent"
        PROPERTY = "property", "Property"

    # Long enough for the Revaluation type to come.
    type = models.CharField(max_length=16, choices=Type)
    kind = models.CharField(max_length=16, choices=Kind, blank=True)
    name = models.CharField(max_length=100)
    notes = models.TextField(blank=True)
    # Four places hold the minor units of any currency.
    opening_balance = models.DecimalField(
        max_digits=24, decimal_places=4, default=Decimal(0)
    )
    opened_on = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("name"), "type", name="account_name_unique_per_type"
            )
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def balance(self) -> Decimal:
        """What the Account holds, derived rather than stored.

        Returns:
            The Opening balance, until transactions add to it.
        """
        return self.opening_balance

    @property
    def icon(self) -> str:
        """The Lucide icon for the Account's Kind.

        Returns:
            The icon's name.
        """
        return ICONS[self.kind]


ICONS = {
    Account.Kind.BANK: "landmark",
    Account.Kind.DEPOSIT: "piggy-bank",
    Account.Kind.CASH: "banknote",
    Account.Kind.INVESTMENT: "chart-line",
    Account.Kind.LENT: "hand-coins",
    Account.Kind.PROPERTY: "house",
}
