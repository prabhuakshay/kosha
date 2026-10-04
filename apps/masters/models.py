"""Accounts, Categories and Tags: where money is, who it moves between, and why."""

from collections import Counter
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
        CREDIT_CARD = "credit_card", "Credit card"
        LOAN = "loan", "Loan"
        MORTGAGE = "mortgage", "Mortgage"
        DEBT = "debt", "Debt"

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
    closed = models.BooleanField(default=False)

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
    def in_use(self) -> bool:
        """Whether anything refers to the Account, so it can't be deleted.

        Returns:
            False, until transactions refer to Accounts.
        """
        return False

    @property
    def icon(self) -> str:
        """The Lucide icon for the Account's Kind, or its type if it has none.

        Returns:
            The icon's name.
        """
        return ICONS[self.kind or self.type]


# In the order each type's list groups them.
KINDS = {
    Account.Type.ASSET: [
        Account.Kind.BANK,
        Account.Kind.DEPOSIT,
        Account.Kind.CASH,
        Account.Kind.INVESTMENT,
        Account.Kind.LENT,
        Account.Kind.PROPERTY,
    ],
    Account.Type.LIABILITY: [
        Account.Kind.CREDIT_CARD,
        Account.Kind.LOAN,
        Account.Kind.MORTGAGE,
        Account.Kind.DEBT,
    ],
}

# What the Owner could actually use, before Credit cards are taken off it.
LIQUID = {
    Account.Kind.BANK,
    Account.Kind.DEPOSIT,
    Account.Kind.CASH,
    Account.Kind.INVESTMENT,
}

ICONS = {
    Account.Type.EXPENSE: "arrow-up-right",
    Account.Type.INCOME: "arrow-down-left",
    Account.Kind.BANK: "landmark",
    Account.Kind.DEPOSIT: "piggy-bank",
    Account.Kind.CASH: "banknote",
    Account.Kind.INVESTMENT: "chart-line",
    Account.Kind.LENT: "hand-coins",
    Account.Kind.PROPERTY: "house",
    Account.Kind.CREDIT_CARD: "credit-card",
    Account.Kind.LOAN: "banknote-arrow-down",
    Account.Kind.MORTGAGE: "calendar-clock",
    Account.Kind.DEBT: "handshake",
}


class Category(models.Model):
    """What money was spent or received for, in or out."""

    # Their light and dark values are theme tokens in the stylesheet.
    class Color(models.TextChoices):
        FOREST = "forest", "Forest"
        SAGE = "sage", "Sage"
        TEAL = "teal", "Teal"
        SKY = "sky", "Sky"
        INDIGO = "indigo", "Indigo"
        PLUM = "plum", "Plum"
        ROSE = "rose", "Rose"
        RUST = "rust", "Rust"
        OCHRE = "ochre", "Ochre"
        OLIVE = "olive", "Olive"
        EARTH = "earth", "Earth"
        STONE = "stone", "Stone"

    # Lucide's names for them.
    class Icon(models.TextChoices):
        SHOPPING_CART = "shopping-cart", "Shopping cart"
        SHOPPING_BAG = "shopping-bag", "Shopping bag"
        UTENSILS = "utensils", "Cutlery"
        COFFEE = "coffee", "Coffee"
        HOUSE = "house", "House"
        SOFA = "sofa", "Sofa"
        WRENCH = "wrench", "Wrench"
        ZAP = "zap", "Electricity"
        DROPLET = "droplet", "Water"
        FLAME = "flame", "Flame"
        WIFI = "wifi", "Wi-Fi"
        SMARTPHONE = "smartphone", "Phone"
        TV = "tv", "TV"
        CAR = "car", "Car"
        FUEL = "fuel", "Fuel"
        BUS = "bus", "Bus"
        TRAIN = "train-front", "Train"
        BIKE = "bike", "Bicycle"
        PLANE = "plane", "Plane"
        PALM = "tree-palm", "Holiday"
        HEART_PULSE = "heart-pulse", "Health"
        PILL = "pill", "Medicine"
        DUMBBELL = "dumbbell", "Fitness"
        SCISSORS = "scissors", "Grooming"
        SHIRT = "shirt", "Clothes"
        GRADUATION_CAP = "graduation-cap", "Education"
        BOOK = "book-open", "Books"
        BABY = "baby", "Children"
        PAW_PRINT = "paw-print", "Pets"
        GIFT = "gift", "Gift"
        HAND_HEART = "hand-heart", "Charity"
        FILM = "film", "Film"
        MUSIC = "music", "Music"
        GAMEPAD = "gamepad-2", "Games"
        PARTY = "party-popper", "Celebration"
        SHIELD = "shield", "Insurance"
        RECEIPT = "receipt", "Bills"
        LANDMARK = "landmark", "Tax"
        BRIEFCASE = "briefcase", "Work"
        LAPTOP = "laptop", "Laptop"
        BANKNOTE = "banknote", "Cash"
        COINS = "coins", "Coins"
        PERCENT = "percent", "Interest"
        TRENDING_UP = "trending-up", "Returns"
        PACKAGE = "package", "Parcel"

    name = models.CharField(max_length=100)
    color = models.CharField(max_length=16, choices=Color)
    icon = models.CharField(max_length=32, choices=Icon, blank=True)
    closed = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "categories"
        constraints = [
            models.UniqueConstraint(Lower("name"), name="category_name_unique")
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def in_use(self) -> bool:
        """Whether anything refers to the Category, so it can't be deleted.

        Returns:
            False, until transactions refer to Categories.
        """
        return False

    @classmethod
    def least_used_color(cls) -> Category.Color:
        """The palette color fewest Categories have, Closed ones included.

        Returns:
            That color, the earliest in the palette if several tie.
        """
        used = Counter(cls.objects.values_list("color", flat=True))
        return min(cls.Color, key=lambda color: used[color])


class Tag(models.Model):
    """The context money moved in, such as a trip or “reimbursable”."""

    name = models.CharField(max_length=100)

    class Meta:
        constraints = [models.UniqueConstraint(Lower("name"), name="tag_name_unique")]

    def __str__(self) -> str:
        return self.name

    @property
    def in_use(self) -> bool:
        """Whether anything refers to the Tag, so it can't be deleted.

        Returns:
            False, until transactions carry Tags.
        """
        return False
