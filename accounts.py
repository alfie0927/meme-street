"""Accounts: passwords, login sessions and the limits that keep sign-ups and logins from being abused.

An account is a name plus a password. The password is never stored: only a salted scrypt hash is (about 60 ms and 16 MB
to check, which makes guessing slow). Logging in gives the browser a random session token; the account's own internal
token (the key everything else uses) never leaves the server for accounts that have a password. Sessions can be ended
one by one or all at once, and an admin can reset a forgotten password.

Accounts that were created before passwords existed keep working with their old token (so nobody is locked out of the
game they were already playing) and are asked to set a password. Once a password is set, only sessions work.

Email. An account can have an email address, which is verified by sending a short code to it and asking for it back.
A verified address does three things: it is the way to recover a forgotten password (a code is mailed to it), it can
be required before anyone may trade (`email_mode` "required"), and each address can belong to only one account, so one
person cannot easily run many accounts. "Alice+1@gmail.com", "a.lice@gmail.com" and "alice@googlemail.com" all count as
the same Gmail address. Codes are stored only as salted hashes, expire after `email_code_minutes`, allow
`email_max_tries` wrong guesses and can be re-sent only after `email_resend_seconds`, at most `email_sends_per_hour`
times an hour per address. The server does the actual sending (see mailer.py); this module only decides what to send.
"""
import hashlib
import hmac
import os
import re
import secrets
from collections import deque

SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 14, 8, 1
MIN_PASSWORD, MAX_PASSWORD = 8, 128
SESSION_DAYS = 30
MAX_SESSIONS = 10                       # per account: logging in on an 11th device ends the oldest session
COMMON_PASSWORDS = {"password", "password1", "12345678", "123456789", "1234567890", "qwertyui", "qwerty123", "iloveyou",
                    "11111111", "00000000", "abcdefgh", "abc12345", "letmein1", "welcome1", "memestreet", "meme street",
                    "stockmarket", "stonksonly"}
RESERVED_NAMES = {"admin", "administrator", "moderator", "mod", "system", "support", "staff", "server", "house", "bank",
                  "memestreet", "meme street", "official", "root", "null", "undefined"}


def hash_password(password, salt=None):
    """A storable record for a password: {"s": salt, "h": hash, "n": cost}. Slow on purpose."""
    salt = salt or os.urandom(16)
    h = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    return {"s": salt.hex(), "h": h.hex(), "n": SCRYPT_N}


def verify_password(password, record):
    try:
        h = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(record["s"]), n=int(record.get("n", SCRYPT_N)),
                           r=SCRYPT_R, p=SCRYPT_P, dklen=32)
        return hmac.compare_digest(h.hex(), record["h"])
    except (KeyError, ValueError, TypeError):
        return False


# Checking a name that does not exist still costs a hash, so the answer takes as long either way.
DUMMY_RECORD = {"s": "00" * 16, "h": "00" * 32, "n": SCRYPT_N}


def password_problem(password, name=""):
    """Why a password is not acceptable, or None."""
    if not isinstance(password, str):
        return "Choose a password"
    if len(password) < MIN_PASSWORD:
        return f"The password needs at least {MIN_PASSWORD} characters"
    if len(password) > MAX_PASSWORD:
        return f"The password can be at most {MAX_PASSWORD} characters"
    low = password.lower()
    if low in COMMON_PASSWORDS or len(set(password)) < 3:
        return "That password is too easy to guess"
    if len(name) >= 3 and name.lower() in low and len(password) < len(name) + 4:
        return "The password should not just be your name"
    return None


def name_problem(name):
    low = name.lower()
    if low in RESERVED_NAMES or low.startswith("bot_") or low.startswith("bot "):
        return "That name is reserved"
    return None


# ---------------------------------------------------------------------------------------------------- email addresses
EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,24}$")
GMAIL_DOMAINS = {"gmail.com", "googlemail.com"}
# Throwaway-inbox services: an address that exists for ten minutes proves nothing. (The admin can add more with the
# `blocked_email_domains` setting.)
DISPOSABLE_DOMAINS = {"mailinator.com", "guerrillamail.com", "guerrillamail.net", "guerrillamail.org", "sharklasers.com",
                      "10minutemail.com", "10minutemail.net", "temp-mail.org", "tempmail.com", "tempmail.net", "tempmailo.com",
                      "yopmail.com", "yopmail.net", "trashmail.com", "trashmail.net", "throwawaymail.com", "getnada.com",
                      "nada.email", "dispostable.com", "maildrop.cc", "mailnesia.com", "fakeinbox.com", "mintemail.com",
                      "spamgourmet.com", "moakt.com", "emailondeck.com", "mohmal.com", "burnermail.io", "inboxkitten.com",
                      "mail.tm", "discard.email", "tmpmail.org", "tmpmail.net", "mytemp.email", "33mail.com", "anonbox.net",
                      "guerrillamailblock.com", "grr.la", "spam4.me", "tempinbox.com", "mailcatch.com", "emailfake.com"}
CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"        # no 0/O or 1/I/L, so a code read off a screen is not misread


def clean_email(raw):
    """(address, error): the address as typed but trimmed and in lower case, or an error message."""
    if not isinstance(raw, str):
        return None, "Enter your email address"
    addr = raw.strip().lower()
    if not addr:
        return None, "Enter your email address"
    if len(addr) > 254 or not EMAIL_RE.match(addr) or ".." in addr or addr.startswith(".") or "@." in addr:
        return None, "That does not look like an email address"
    return addr, None


def canonical_email(addr):
    """The address two spellings of the same mailbox share. Gmail ignores dots and everything after a plus sign in the
    part before the @, and other providers (nearly all) ignore the plus part, so "a.b+x@gmail.com" is "ab@gmail.com"."""
    local, _, domain = addr.lower().partition("@")
    if domain in GMAIL_DOMAINS:
        domain = "gmail.com"
        local = local.replace(".", "")
    return local.split("+", 1)[0] + "@" + domain


def email_problem(addr, extra_blocked=()):
    """Why an (already clean) address is not acceptable, or None."""
    domain = addr.rpartition("@")[2]
    blocked = DISPOSABLE_DOMAINS | {str(d).lower() for d in extra_blocked}
    if any(domain == d or domain.endswith("." + d) for d in blocked):
        return "Please use a real email address, not a disposable one"
    return None


def mask_email(addr):
    """What the owner is shown of their own address: a***@gmail.com (never the whole thing in a page that others could
    see over their shoulder, and never in anything public)."""
    if not addr or "@" not in addr:
        return None
    local, _, domain = addr.partition("@")
    return local[:1] + "***@" + domain


def new_code(purpose):
    """A fresh code: six digits to verify an address, eight letters and digits to reset a password."""
    if purpose == "verify":
        return "%06d" % secrets.randbelow(10 ** 6)
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))


def _code_hash(salt, code):
    wanted = "".join(c for c in str(code) if c.isalnum()).upper()
    return hashlib.sha256((salt + wanted).encode("utf-8")).hexdigest()


class Limiter:
    """Counts events per key inside a sliding window (for failed logins and sign-ups)."""

    def __init__(self):
        self.hits = {}

    def count(self, key, window, now):
        q = self.hits.get(key)
        if not q:
            return 0
        while q and now - q[0] > window:
            q.popleft()
        if not q:
            del self.hits[key]
            return 0
        return len(q)

    def add(self, key, now):
        if len(self.hits) > 20000:                       # never grow without bound
            self.hits.clear()
        self.hits.setdefault(key, deque(maxlen=200)).append(now)

    def clear(self, key):
        self.hits.pop(key, None)

    def retry_after(self, key, window, now):
        q = self.hits.get(key)
        return max(1, int(window - (now - q[0]))) if q else 0


def _hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AccountsMixin:
    """Part of the Engine: who an account is, its sessions, and which accounts seem to be the same person."""

    def _init_accounts(self):
        self.sessions = {}                 # sha256(session token) -> {"p": the account's token, "t": made, "seen": last used}
        self.ip_salt = secrets.token_hex(8)  # so an address is never stored, only a salted tag of it
        self.mail_codes = {}               # "verify:<token>" or "reset:<token>" -> {"salt","h","exp","tries","email","t"}
        self.mail_sent = {}                # canonical address -> times a code was sent to it (last hour)
        self.email_owner = {}              # canonical address -> account token, for verified addresses only
        self.default_email_mode = "off"    # what `email_mode` means when no setting names one (the server makes it "optional" once real mail is set up)

    # ---- creating accounts
    def ip_tag(self, ip):
        return hashlib.sha256((self.ip_salt + str(ip)).encode("utf-8")).hexdigest()[:12]

    def register(self, name, record, ip=None):
        """A new account with a password. Returns (player, error)."""
        p, err = self.join(name)
        if not p:
            return None, err
        p.pw = record
        if ip is not None:
            p.ips = [self.ip_tag(ip)]
        return p, ""

    def password_record(self, name):
        """(account token, password record) for a login attempt, or (None, None)."""
        p = self._human_named(name)
        return (p.token, p.pw) if p and p.pw else (None, None)

    # ---- sessions
    def new_session(self, p, ip=None):
        token = secrets.token_urlsafe(32)
        mine = sorted((v["t"], k) for k, v in self.sessions.items() if v["p"] == p.token)
        for _, k in mine[:max(0, len(mine) - MAX_SESSIONS + 1)]:
            self.sessions.pop(k, None)
        self.sessions[_hash_token(token)] = {"p": p.token, "t": self.now, "seen": self.now}
        if ip is not None:
            tag = self.ip_tag(ip)
            if tag not in p.ips:
                p.ips = (p.ips + [tag])[-5:]
        return token

    def player_for(self, token):
        """The player a presented token belongs to, or None. Session tokens work for everyone; the account's old
        permanent token only works while the account has no password (see the module note)."""
        if not token:
            return None
        key = _hash_token(token)
        s = self.sessions.get(key)
        if s is not None:
            if self.now - s["seen"] > SESSION_DAYS * 86400:
                self.sessions.pop(key, None)
                return None
            p = self.by_token.get(s["p"])
            if p is None:
                self.sessions.pop(key, None)
                return None
            if self.now - s["seen"] > 3600:
                s["seen"] = self.now
            return p
        p = self.by_token.get(token)
        if p is not None and p.pw is None and not p.bot:
            return p
        return None

    def end_session(self, token):
        return self.sessions.pop(_hash_token(token), None) is not None

    def end_all_sessions(self, p, keep=None):
        keep_key = _hash_token(keep) if keep else None
        gone = [k for k, v in self.sessions.items() if v["p"] == p.token and k != keep_key]
        for k in gone:
            del self.sessions[k]
        return len(gone)

    def set_password(self, p, record):
        """Set or change an account's password. The caller has already checked the old one (and ends the other
        sessions)."""
        p.pw = record
        return True

    def reset_password(self, name, record):
        """Admin: replace a forgotten password and end every session of that account."""
        p = self._human_named(name)
        if p is None:
            return None
        p.pw = record
        self.end_all_sessions(p)
        return p

    # ---- email: verifying an address, and recovering a password with it
    def email_mode(self):
        """"off" (no email asked for), "optional" (asked for, never needed) or "required" (a verified address is needed
        before anyone can trade, enter a contest or chat). With no setting it is "off", until the server finds that
        mail can really be sent, and then "optional": asking for an address that no mail will ever reach would only
        confuse people."""
        mode = self.settings.get("email_mode", self.default_email_mode)
        return mode if mode in ("off", "optional", "required") else self.default_email_mode

    def email_gate(self, p):
        """The reason this player may not play yet, or None. Only bites in "required" mode."""
        if self.email_mode() == "required" and not p.bot and not p.email_verified:
            return "Verify your email address to play: open Profile, enter your email and then the code we send you"
        return None

    def email_check(self, raw):
        """(address, error) for an address someone wants to use: well formed, not a throwaway inbox, and not already
        verified on another account."""
        addr, err = clean_email(raw)
        if err:
            return None, err
        err = email_problem(addr, self.settings.get("blocked_email_domains", ()))
        if err:
            return None, err
        return addr, None

    def _mail_wait(self, purpose, token, canon):
        """Seconds until another code may be sent for this account and address (0 if one may be sent now)."""
        gap = float(self.settings.get("email_resend_seconds", 60))
        entry = self.mail_codes.get(purpose + ":" + token)
        if entry and self.now - entry["t"] < gap:
            return int(gap - (self.now - entry["t"])) + 1
        times = [t for t in self.mail_sent.get(canon, []) if self.now - t < 3600]
        if len(times) >= int(self.settings.get("email_sends_per_hour", 5)):
            return int(3600 - (self.now - times[0])) + 1
        return 0

    def _issue_code(self, purpose, token, addr):
        """Make and remember a code (only its hash is kept); the caller mails the returned code."""
        code = new_code(purpose)
        salt = secrets.token_hex(8)
        self.mail_codes[purpose + ":" + token] = {"salt": salt, "h": _code_hash(salt, code), "tries": 0, "email": addr, "t": self.now,
                                                  "exp": self.now + 60 * float(self.settings.get("email_code_minutes", 15))}
        canon = canonical_email(addr)
        if len(self.mail_sent) > 5000:
            self.mail_sent.clear()
        self.mail_sent[canon] = [t for t in self.mail_sent.get(canon, []) if self.now - t < 3600] + [self.now]
        return code

    def _check_code(self, purpose, token, code):
        """(ok, error). A wrong guess is counted; too many wrong guesses (or time running out) cancels the code."""
        key = purpose + ":" + token
        entry = self.mail_codes.get(key)
        if entry is None:
            return False, "No code is waiting. Ask for a new one."
        if self.now > entry["exp"]:
            del self.mail_codes[key]
            return False, "That code has expired. Ask for a new one."
        entry["tries"] += 1
        if not hmac.compare_digest(_code_hash(entry["salt"], code), entry["h"]):
            if entry["tries"] >= int(self.settings.get("email_max_tries", 5)):
                del self.mail_codes[key]
                return False, "Too many wrong codes. Ask for a new one."
            return False, "That code is not right"
        return True, None

    def email_begin(self, p, raw):
        """Start verifying an address for this account. Returns (ok, message, code, address, wait): the caller mails
        the code to the address."""
        addr, err = self.email_check(raw)
        if err:
            return False, err, None, None, 0
        canon = canonical_email(addr)
        owner = self.email_owner.get(canon)
        if owner and owner != p.token:
            return False, "That email address is already used by another account", None, None, 0
        if owner == p.token and p.email_verified:
            return False, "That address is already verified on your account", None, None, 0
        wait = self._mail_wait("verify", p.token, canon)
        if wait:
            return False, f"A code was sent recently. You can ask for another one in {wait} s.", None, None, wait
        p.email_pending = addr
        code = self._issue_code("verify", p.token, addr)
        return True, f"We sent a {self.settings.get('email_code_minutes', 15)}-minute code to {mask_email(addr)}", code, addr, 0

    def email_resend(self, p):
        """Send the code for the address that is waiting to be verified again."""
        addr = p.email_pending or (p.email if not p.email_verified else None)
        if not addr:
            return False, "There is no address waiting to be verified", None, None, 0
        return self.email_begin(p, addr)

    def email_confirm(self, p, code):
        """The player typed the code from their email. Returns (ok, message)."""
        entry = self.mail_codes.get("verify:" + p.token)
        ok, err = self._check_code("verify", p.token, code)
        if not ok:
            return False, err
        addr, canon = entry["email"], canonical_email(entry["email"])
        owner = self.email_owner.get(canon)
        if owner and owner != p.token:                       # someone else verified this address first
            self.mail_codes.pop("verify:" + p.token, None)
            return False, "That email address is already used by another account"
        if p.email and p.email_verified:
            self.email_owner.pop(canonical_email(p.email), None)
        p.email, p.email_verified, p.email_pending = addr, True, None
        self.email_owner[canon] = p.token
        self.mail_codes.pop("verify:" + p.token, None)
        for q in self.players.values():                      # an unverified claim on the same address is void now
            if q is not p and q.email and not q.email_verified and canonical_email(q.email) == canon:
                q.email = q.email_pending = None
            elif q is not p and q.email_pending and canonical_email(q.email_pending) == canon:
                q.email_pending = None
        return True, "Your email address is verified"

    def email_clear(self, p):
        """Remove an account's address (admin support action)."""
        if p.email and p.email_verified:
            self.email_owner.pop(canonical_email(p.email), None)
        p.email = p.email_pending = None
        p.email_verified = False
        self.mail_codes.pop("verify:" + p.token, None)

    def email_force_verified(self, p):
        """Admin support action: accept the address on the account as verified without a code."""
        addr = p.email_pending or p.email
        if not addr:
            return False, "That account has no email address"
        canon = canonical_email(addr)
        if self.email_owner.get(canon, p.token) != p.token:
            return False, "Another account already has that address verified"
        if p.email and p.email_verified:
            self.email_owner.pop(canonical_email(p.email), None)
        p.email, p.email_verified, p.email_pending = addr, True, None
        self.email_owner[canon] = p.token
        self.mail_codes.pop("verify:" + p.token, None)
        return True, "Marked as verified"

    def _human_named(self, name):
        low = str(name).strip().lower()
        return next((x for x in self.players.values() if not x.bot and x.name.lower() == low), None)

    def recovery_begin(self, name):
        """A forgotten password. Returns (code, address) when a code should be mailed, else None. The caller shows the
        same answer either way, so nobody can use this to find out which names or addresses have accounts."""
        p = self._human_named(name)
        if p is None or not p.email_verified or not p.email:
            return None
        if self._mail_wait("reset", p.token, canonical_email(p.email)):
            return None
        return self._issue_code("reset", p.token, p.email), p.email

    def recovery_finish(self, name, code, record):
        """Check the code and set the new password. Returns (player, error); ends every session of the account."""
        p = self._human_named(name)
        if p is None:
            return None, "That code is not right or has expired"
        ok, err = self._check_code("reset", p.token, code)
        if not ok:
            return None, err
        p.pw = record
        self.end_all_sessions(p)
        self.mail_codes.pop("reset:" + p.token, None)
        return p, None

    def _index_emails(self):
        self.email_owner = {canonical_email(p.email): p.token for p in self.players.values()
                            if p.email and p.email_verified and not p.bot}

    # ---- keeping an eye on duplicate accounts
    def account_stats(self):
        humans = [p for p in self.players.values() if not p.bot]
        by_ip = {}
        for p in humans:
            for tag in p.ips:
                by_ip.setdefault(tag, []).append(p)
        groups = [{"names": sorted(x.name for x in ps), "accounts": len(ps)} for ps in by_ip.values() if len(ps) >= 2]
        groups.sort(key=lambda g: -g["accounts"])
        return {"accounts": len(humans), "with_password": sum(1 for p in humans if p.pw), "legacy": sum(1 for p in humans if not p.pw),
                "sessions": len(self.sessions), "shared_address": groups[:30], "email_mode": self.email_mode(),
                "with_email": sum(1 for p in humans if p.email), "email_verified": sum(1 for p in humans if p.email_verified),
                "unverified": sorted(p.name for p in humans if not p.email_verified)[:50]}

    def accounts_dump(self):
        return {"sessions": self.sessions, "ip_salt": self.ip_salt, "mail_codes": self.mail_codes}

    def accounts_load(self, d):
        self.ip_salt = str(d.get("ip_salt") or self.ip_salt)
        self.sessions = {k: v for k, v in dict(d.get("sessions", {})).items()
                         if isinstance(v, dict) and v.get("p") in self.by_token}
        self.mail_codes = {k: v for k, v in dict(d.get("mail_codes", {})).items()
                           if isinstance(v, dict) and k.partition(":")[2] in self.by_token
                           and all(f in v for f in ("salt", "h", "tries", "email", "t", "exp")) and v["exp"] > self.now}
        self._index_emails()
