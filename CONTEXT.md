# Kosha

A self-hosted personal finance app: one person's treasury, on infrastructure they control.

## Language

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
A fresh Passkey or Authenticator app check, good for 10 minutes, that the Owner must pass before changing a Way to sign in, the password or the Recovery codes. Finishing a sign-in counts as one, even by Recovery code, so an Owner who lost their Authenticator app can set up another. Shown on screen as "Confirm it's you".
_Avoid_: sudo, re-auth, step-up

**Session**:
One browser or installed app signed in as the Owner. Lasts 30 days from its last visit. The Owner can see every Session and sign out all but the current one.

**Pause**:
An hour in which an address can't sign in, after 5 wrong passwords or codes from it.
_Avoid_: lockout, ban

**Security log**:
The permanent record of everything that happened to how Kosha is signed in to: sign-ins, wrong passwords and codes, Pauses, and every change to a Way to sign in, the password or the Recovery codes. The Owner can read it but never edit or clear it. A sign-in from an address or device no earlier sign-in used also emails the Owner.
