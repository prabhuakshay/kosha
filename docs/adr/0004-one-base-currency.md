# One Base currency per install

Every amount in Kosha is in the install's Base currency, set in Settings and
INR by default. There is no per-Account currency and nothing is ever
converted: changing the Base currency relabels every amount as it stands.
Multi-currency means exchange rates, converted net worth and reports that
mix currencies, which is a large feature for a case most Owners don't have,
so we leave it out on purpose rather than half-build it.

## Consequences

- The Base currency decides how amounts are written (symbol, grouping such
  as lakhs for INR, decimal places) and the precision they are stored at.
- Adding multi-currency later is a migration of every amount, not a setting.
