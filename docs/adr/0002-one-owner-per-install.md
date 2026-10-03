# One Owner per install

A Kosha install belongs to one person. There is no sign-up, no invite and no
second login: the first person to Claim an empty install, by entering the
Setup code printed in the server's log, becomes its Owner, and every Claim
route is gone once an Owner exists.

Personal finances are one person's, and a self-hosted install is cheap, so a
household member who wants Kosha runs their own. Allowing many logins would
mean scoping every record to a user, deciding what is shared, and building
sign-up, invites and roles, all for a case we don't serve.

## Consequences

- Records carry no owner field; everything in the database is the Owner's.
- A public URL can't hand the first visitor the keys, so Claim needs the
  Setup code, which only someone who can read the server's log has seen.
- An Owner who loses every Way to sign in gets back in from the server
  (`manage.py break_glass`), since there is no other login to help them.
- Going multi-user later is a migration of every model, not a feature flag.
