# Kosha

A self-hosted personal finance app: one person's treasury, on infrastructure they control.

## Language

### Signing in

**Owner**:
The one person a Kosha install belongs to, and its only login. There is no sign-up and no second login.
_Avoid_: user, account (Account will mean a financial account)

**Claim**:
Making an empty install yours: entering the Setup code, then the Owner's name, email and password, then setting up a first Way to sign in. Possible only while the install has no Owner.

**Setup code**:
The code, shown only in the server's log, that proves the person claiming an install runs it.

**Way to sign in**:
A Passkey or an Authenticator app. Signing in takes a Passkey alone, or the password plus a code from the Authenticator app. A signed-in Owner without a Way to sign in can do nothing until they set one up, and the last one can't be removed.
_Avoid_: factor, device, 2FA method

**Passkey**:
A credential held by a phone, computer or security key that signs the Owner in on its own. The Owner may have several.

**Authenticator app**:
An app that shows a new 6-digit code every 30 seconds. The Owner has at most one; setting up another replaces it.
_Avoid_: TOTP device, OTP

**Recovery code**:
One of ten single-use codes, shown once, that stand in for the Authenticator app's code when it is lost. Not a Way to sign in.
_Avoid_: backup code

**Confirmation**:
A fresh Passkey or Authenticator app check, good for 10 minutes, that the Owner must pass before seeing Security or changing a Way to sign in, the password or the Recovery codes. Finishing a sign-in counts as one, even by Recovery code, so an Owner who lost their Authenticator app can set up another. Shown on screen as "Confirm it's you".
_Avoid_: sudo, re-auth, step-up

**Session**:
One browser or installed app signed in as the Owner. Lasts 30 days from its last visit. The Owner can see every Session and sign out all but the current one.

**Pause**:
An hour in which an address can't sign in, after 5 wrong passwords or codes from it.
_Avoid_: lockout, ban

**Security log**:
The permanent record of everything that happened to how Kosha is signed in to: sign-ins, wrong passwords and codes, Pauses, every change to a Way to sign in, the password or the Recovery codes, and every device that turns reminders on or off. The Owner can read it but never edit or clear it. A sign-in from an address or device no earlier sign-in used also emails the Owner.

### Money

**Base currency**:
The one currency every amount in Kosha is in, set in Settings. INR unless the Owner changes it.
_Avoid_: default currency, home currency

**Time zone**:
The Owner's time zone, set in Settings, which decides what today is: the latest a Transaction can be dated, when a Due comes round and when reminders go out.

**Account**:
Any Asset account, Liability, Expense account, Income account, or Revaluation. Its name is unique among Accounts of the same type, ignoring case. Never created from typed text, only on purpose.

**Asset account**:
An Account holding money the Owner has: a Bank, Deposit, Cash, Investment, Lent or Property account. Bank is an account money comes in to and is spent from, whatever the bank calls it; Deposit is money put away for a fixed term, such as a fixed or recurring deposit. Lent is money others owe the Owner; Property is something they own that isn't money, such as a house, land, a vehicle or gold.

**Liability**:
An Account holding money the Owner owes, which they can also spend from: a Credit card, Loan, Mortgage or Debt to a person.
_Avoid_: debt account

**Kind**:
What sort of Asset account or Liability an Account is, such as Deposit or Credit card. It can change within the same type but never from an Asset account to a Liability or back.
_Avoid_: role, subtype

**Expense account**:
Someone the Owner pays: a shop, a landlord, a utility. Says who money went to, never what it was for.
_Avoid_: payee, merchant, vendor

**Income account**:
Someone who pays the Owner: an employer, a client, a tenant.
_Avoid_: revenue account, payer, source

**Revaluation**:
The one Account Kosha keeps for itself, on the other side of every change in what a Property or Investment account is worth. The Owner can't create, edit or delete it, and it counts as neither spending nor income.
_Avoid_: depreciation, adjustment, unrealised gains

**Net worth**:
Everything in Asset accounts minus everything in Liabilities.

**Liquid net worth**:
Net worth counting only Bank, Deposit, Cash and Investment accounts, less Credit cards: what the Owner could actually use.

**Opening balance**:
What an Asset account or Liability held at the start of the day the Owner started tracking it in Kosha. Nothing can be dated before that day.
_Avoid_: initial balance, starting balance

**Closed**:
An Account the Owner no longer uses, hidden from everyday lists but kept with its history. Only an Account with nothing in it can be Closed, and it can be reopened. An Account that nothing refers to can be deleted outright instead; its History keeps that it existed.
_Avoid_: archived, inactive

**Category**:
What money was spent or received for, such as Groceries or Salary. One flat list, usable on money going out or coming in, so a refund under a Category takes it off that Category's spending. Can be Closed like an Account.
_Avoid_: expense type, head

**Tag**:
A label for the context money moved in, such as a trip or "reimbursable". Any number can be put on the same movement of money, and typing a new one creates it. Never Closed, only deleted.
_Avoid_: label, project

**History**:
The permanent record of every change to an Account, Category, Tag, Rule, Recurring Transaction or Setting, every edit or deletion of a Transaction, and every Reconciliation undone: what changed, from what to what, and when, including deletions. The Owner can read it but never edit or clear it. Separate from the Security log.
_Avoid_: audit log, change log, activity

### Transactions

**Transaction**:
An amount moving from one Account to another on one day. Spending, Income, Transfer or a Value update, decided by its two Accounts. Never split into parts: a bill paid for two reasons is two Transactions.
_Avoid_: entry, journal, movement, split

**Spending**:
A Transaction from an Asset account or Liability to an Expense account.
_Avoid_: withdrawal, expense, debit

**Income**:
A Transaction from an Income account to an Asset account or Liability.
_Avoid_: deposit, credit, revenue

**Transfer**:
A Transaction between two Asset accounts or Liabilities, such as paying a Credit card, lending to a friend or buying a house. Neither Spending nor Income.
_Avoid_: move

**Value update**:
A Transaction between a Property or Investment account and Revaluation, entered as what the Account is now worth. Neither Spending nor Income.
_Avoid_: revaluation (that is the Account), mark to market, adjustment

**Recurring Transaction**:
A Transaction that repeats on a schedule, such as an EMI or a credit card payment. It never posts itself: each time it comes round it makes a Due.
_Avoid_: bill, subscription, standing instruction, scheduled transaction

**Due**:
One coming round of a Recurring Transaction, waiting for the Owner to confirm it, perhaps with a different amount, or skip it. Nothing moves until it is confirmed.
_Avoid_: reminder, upcoming, pending

**Import**:
A statement file for one Asset account or Liability, whose lines the Owner reviews before any becomes a Transaction. The file is kept with it.
_Avoid_: upload, sync

**Rule**:
An instruction for sorting Import lines, such as "a line containing SWIGGY is Spending at Swiggy under Food". Made on purpose by the Owner, never guessed.
_Avoid_: filter, mapping, automation

**Activity**:
The list of every Transaction.
_Avoid_: ledger, register, feed

**Reconciliation**:
Checking an Asset account or Liability against a statement: the Owner enters the statement's closing balance and date, and Kosha shows its own balance on that date beside it. When they agree, every Transaction in the Account up to that date becomes Reconciled. Only the latest can be undone.
_Avoid_: clearing, matching

**Reconciled**:
A Transaction a Reconciliation has vouched for. Changing or deleting one asks first.
_Avoid_: cleared, locked
