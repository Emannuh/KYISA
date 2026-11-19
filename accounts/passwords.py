"""
Temporary password generation for system-created accounts and admin resets.

* Cryptographically secure (``secrets``), never ``random``.
* No look-alike characters (l, I, 1, O, 0), so passwords copied by hand
  from an email aren't mistyped.
* Always contains upper case, lower case and digits, so it passes the
  configured AUTH_PASSWORD_VALIDATORS (not numeric-only, not common).
"""
import secrets

UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"   # no I, O
LOWER = "abcdefghijkmnpqrstuvwxyz"   # no l, o
DIGITS = "23456789"                  # no 0, 1
ALPHABET = UPPER + LOWER + DIGITS


def generate_temp_password(length=12):
    """Return a random, unambiguous temporary password of ``length`` characters."""
    if length < 8:
        raise ValueError("Temporary passwords must be at least 8 characters.")
    chars = [secrets.choice(UPPER), secrets.choice(LOWER), secrets.choice(DIGITS)]
    chars += [secrets.choice(ALPHABET) for _ in range(length - len(chars))]
    # Shuffle so the guaranteed character classes aren't always at the front.
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]
    return "".join(chars)
