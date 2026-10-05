# A scheduler service for reminders

Recurring Transactions must remind the Owner when something is Due even if
they haven't opened Kosha, so something has to run on a clock. We run a
third Compose service from the same image, `manage.py scheduler`, a small
loop that wakes every few minutes and does whatever is owed, catching up on
anything missed while it was down. Host cron would make every self-hoster
configure it outside Compose, and Django's tasks framework with a worker
brings a queue we don't need yet.

The scheduler only ever notifies. It never posts a Transaction: every Due
waits for the Owner to confirm it, so a wrong amount never reaches a balance
unseen.

## Consequences

- Production runs two long-running processes from one image; the scheduler
  needs the database and the email and Web Push settings but no port.
- Jobs must be safe to run late or twice, since a restart catches up.
