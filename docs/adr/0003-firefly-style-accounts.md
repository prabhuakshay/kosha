# Firefly-style Accounts

Kosha models money the way Firefly III does: an Account is an Asset account,
a Liability, an Expense account or an Income account, and every movement of
money goes from one Account to another. Expense and Income accounts are the
people and shops on the other side, not what the money was for; that is a
Category, and the context it moved in is a Tag. We kept who, what and why
apart because they vary independently: Amazon is Household one day and Books
the next, Groceries comes from three different shops, and a trip spans many
of both. GnuCash-style categories-as-accounts would lose "how much did I
spend at Amazon", and categories-as-tags would leave budgets nothing firm to
hang on.

We part from Firefly in two places. A credit card is a Liability that can be
spent from directly, not an Asset account with a "credit card" role whose
balance goes negative, because it is money the Owner owes. A Liability only
ever runs one way, so money the Owner has lent is an Asset account of Kind
Lent, not a Liability "owed to me".

Things the Owner owns that aren't money (a house, land, a car, gold) are
Asset accounts of Kind Property, so buying one is a transfer, not spending,
and a Mortgage has the house to set against it. Recording such a purchase as
an expense would leave every mortgaged homeowner with a large negative net
worth. A Property's value is updated by hand against the system-owned
Revaluation account, never depreciated automatically, because straight-line
and written-down-value schedules are tax conventions, not resale value.
Investment accounts are updated the same way, as a value the Owner reads off
their statement, so that a mutual fund shows what it is worth rather than
what was paid into it; Kosha tracks no units, holdings or prices.
Phones, laptops and furniture stay expenses: they have no real resale market
and nobody's net worth hinges on them.

## Consequences

- A Kind is a label that groups Accounts and picks their icon; it can change
  within a type but never between Asset account and Liability, since that
  would flip the sign of its balance.
- Expense accounts, Income accounts and Categories are only ever created on
  purpose, never from typed text, so their lists stay free of near-duplicates.
  Tags are the exception and are created by typing them.
