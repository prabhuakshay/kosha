"""The lists of Accounts, one per type: their routes and what they say."""

from dataclasses import dataclass

from apps.masters.forms import AccountForm, BalanceAccountForm
from apps.masters.models import KINDS, Account


@dataclass(frozen=True)
class Listing:
    """A list of Accounts of one type: its routes and what it says."""

    type: Account.Type
    route: str
    plural: str
    title: str
    noun: str
    lede: str
    example: str
    opening_note: str = ""

    @property
    def kinds(self) -> list[Account.Kind]:
        """The Kinds the list groups by, if its type has any."""
        return KINDS.get(self.type, [])

    @property
    def form(self) -> type[AccountForm]:
        """The form adding or changing one of its Accounts."""
        return BalanceAccountForm if self.kinds else AccountForm

    @property
    def detail(self) -> str:
        """The route name of an Account's detail."""
        return f"masters:{self.route}"

    @property
    def new(self) -> str:
        """The route name of the form adding an Account."""
        return f"masters:new_{self.route}"

    @property
    def edit(self) -> str:
        """The route name of the form editing an Account."""
        return f"masters:edit_{self.route}"

    @property
    def close(self) -> str:
        """The route name that Closes an Account."""
        return f"masters:close_{self.route}"

    @property
    def reopen(self) -> str:
        """The route name that Reopens an Account."""
        return f"masters:reopen_{self.route}"

    @property
    def delete(self) -> str:
        """The route name that deletes an Account."""
        return f"masters:delete_{self.route}"


ASSETS = Listing(
    type=Account.Type.ASSET,
    route="asset",
    plural="assets",
    title="Assets",
    noun="asset account",
    example="HDFC Savings",
    lede="Money you have, or something you own.",
    opening_note="What it held when you started tracking it. Use a minus sign "
    "only if it was overdrawn.",
)
LIABILITIES = Listing(
    type=Account.Type.LIABILITY,
    route="liability",
    plural="liabilities",
    title="Liabilities",
    noun="liability",
    example="HDFC Regalia",
    lede="Money you owe, even if you can spend from it, such as a credit card.",
    opening_note="What you owed when you started tracking it. Use a minus sign "
    "only if you were in credit.",
)
INCOME = Listing(
    type=Account.Type.INCOME,
    route="income_account",
    plural="income",
    title="Income",
    noun="income account",
    example="Acme Corp",
    lede="Someone who pays you, such as an employer, a client or a tenant.",
)
EXPENSES = Listing(
    type=Account.Type.EXPENSE,
    route="expense_account",
    plural="expenses",
    title="Expenses",
    noun="expense account",
    example="BigBasket",
    lede="Someone you pay, such as a shop, a landlord or a utility.",
)
LISTINGS = {
    listing.type: listing for listing in (ASSETS, LIABILITIES, INCOME, EXPENSES)
}
