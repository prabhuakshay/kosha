"""Net worth: what the Owner has, less what they owe."""

from dataclasses import dataclass
from decimal import Decimal

from apps.masters.models import LIQUID, Account


@dataclass(frozen=True)
class Worth:
    """The open Asset accounts and Liabilities, added up."""

    assets: Decimal
    liabilities: Decimal
    liquid: Decimal
    no_accounts: bool

    @property
    def net(self) -> Decimal:
        """Everything in Asset accounts minus everything in Liabilities."""
        return self.assets - self.liabilities

    @property
    def asset_share(self) -> int | None:
        """What the Owner has as a percent of what they have and owe, if either."""
        owned, owed = max(self.assets, 0), max(self.liabilities, 0)
        if not owned + owed:
            return None
        return round(owned * 100 / (owned + owed))


def worth() -> Worth:
    """Add up the open Asset accounts and Liabilities, as their lists do.

    Returns:
        The totals.
    """
    accounts = list(
        Account.objects.filter(
            type__in=[Account.Type.ASSET, Account.Type.LIABILITY], closed=False
        )
    )

    def total(type_: Account.Type, kinds: set[Account.Kind] | None = None) -> Decimal:
        return sum(
            (
                a.balance
                for a in accounts
                if a.type == type_ and (kinds is None or a.kind in kinds)
            ),
            Decimal(0),
        )

    return Worth(
        assets=total(Account.Type.ASSET),
        liabilities=total(Account.Type.LIABILITY),
        liquid=total(Account.Type.ASSET, LIQUID)
        - total(Account.Type.LIABILITY, {Account.Kind.CREDIT_CARD}),
        no_accounts=not accounts,
    )
