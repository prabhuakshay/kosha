# No split Transactions

A Transaction is one amount from one Account to another, with at most one
Category. Unlike Firefly III, Kosha has no splits: money paid for two reasons
is two Transactions. Splits would turn every entry screen into a list of
lines with a running total and make budgets, reports, import and
reconciliation work on lines instead of Transactions, all for a case that
is rare in one person's finances. The common repeating one, a loan EMI that
is part principal (a Transfer) and part interest (Spending), is covered by
two Recurring Transactions due on the same day.

## Consequences

- A single statement line that stands for two Transactions, such as an EMI,
  is broken into two when imported, and matched by their total.
- Adding splits later is a migration of every Transaction into one with a
  single split, plus new entry screens.
