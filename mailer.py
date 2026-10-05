"""Sending email (verification and password-recovery codes).

The game only needs plain text mail, so this uses Python's own `smtplib` and needs no extra package. Any email service
can be used, because all of them speak SMTP (Resend, Brevo, Postmark, Amazon SES, Mailgun, a Gmail app password...).
It is set up with environment variables:

    SMTP_HOST       mail server, e.g. smtp.resend.com        (required; with none, mail is not sent but kept, see below)
    SMTP_PORT       587 (STARTTLS, the usual), 465 (TLS from the start) or 25            default 587
    SMTP_USER       the login name the service gave you
    SMTP_PASSWORD   the password or API key the service gave you
    MAIL_FROM       the sender, e.g. "Meme Street <no-reply@yourdomain.com>"    (must be an address the service allows)
    SMTP_SECURITY   starttls, ssl or none                                       default: ssl on port 465, else starttls

With no SMTP_HOST the mailer runs in *console mode*: nothing leaves the machine, the message (code included) is
printed in the server log and shown on the admin page under "Mail", so you can try the whole flow on your own computer
and, during a closed test, pass a code to a tester by hand. A real deployment must set SMTP_HOST: a code shown to the
admin is only as private as the admin.

Sending happens on a background thread so a slow mail server can never hold up the game, and a failed send is tried
again twice. Messages go through `send()`, which never raises and never blocks."""
import logging
import os
import queue
import smtplib
import ssl
import threading
import time
from collections import deque
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

logger = logging.getLogger(__name__)


class Mailer:
    def __init__(self, host=None, port=587, user=None, password=None, sender=None, security=None, transport=None,
                 retry_delays=(5, 30)):
        self.host = host or None
        self.port = int(port or 587)
        self.user = user or None
        self.password = password or None
        self.sender = sender or (f"Meme Street <no-reply@{self.host}>" if self.host else "Meme Street <no-reply@localhost>")
        self.security = (security or ("ssl" if self.port == 465 else "starttls")).lower()
        self.transport = transport            # tests pass a function(message) here instead of a real mail server
        self.retry_delays = tuple(retry_delays)
        self.log = deque(maxlen=60)           # newest last: what was sent (or tried) recently, for the admin page
        self.sent = self.failed = 0
        self._queue = queue.Queue(maxsize=1000)
        self._thread = None
        self._lock = threading.Lock()

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        return cls(host=env.get("SMTP_HOST"), port=env.get("SMTP_PORT") or 587, user=env.get("SMTP_USER"),
                   password=env.get("SMTP_PASSWORD"), sender=env.get("MAIL_FROM"), security=env.get("SMTP_SECURITY"))

    @property
    def configured(self):
        """True when mail really leaves the machine (an SMTP server is set, or a test transport stands in for one)."""
        return bool(self.host or self.transport)

    def status(self):
        return {"configured": self.configured, "host": self.host, "port": self.port if self.host else None,
                "sender": self.sender, "sent": self.sent, "failed": self.failed, "queued": self._queue.qsize()}

    def recent(self):
        """The recent messages, newest first. Only console mode keeps the body (it is the way to read a code)."""
        return [dict(x) for x in reversed(self.log)]

    # ---- sending
    def send(self, to, subject, body):
        """Queue a message. Returns at once; `True` if it was accepted for sending."""
        entry = {"t": time.time(), "to": to, "subject": subject, "state": "queued", "error": None}
        if not self.configured:
            entry["state"] = "console"
            entry["body"] = body
            self.log.append(entry)
            logger.warning("EMAIL NOT CONFIGURED: would send to %s: %s\n%s", to, subject, body)
            return True
        self.log.append(entry)
        try:
            self._queue.put_nowait((entry, to, subject, body))
        except queue.Full:
            entry["state"], entry["error"] = "dropped", "the mail queue is full"
            self.failed += 1
            return False
        self._ensure_thread()
        return True

    def _ensure_thread(self):
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._worker, name="mailer", daemon=True)
                self._thread.start()

    def _message(self, to, subject, body):
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = self.sender, to, subject
        msg["Date"] = formatdate(localtime=False)
        msg["Message-ID"] = make_msgid(domain=(self.sender.rpartition("@")[2].rstrip(">") or "localhost"))
        msg.set_content(body)
        return msg

    def _deliver(self, msg):
        if self.transport is not None:
            self.transport(msg)
            return
        context = ssl.create_default_context()
        if self.security == "ssl":
            server = smtplib.SMTP_SSL(self.host, self.port, timeout=20, context=context)
        else:
            server = smtplib.SMTP(self.host, self.port, timeout=20)
        with server:
            server.ehlo()
            if self.security == "starttls":
                server.starttls(context=context)
                server.ehlo()
            if self.user:
                server.login(self.user, self.password or "")
            server.send_message(msg)

    def _worker(self):
        while True:
            try:
                entry, to, subject, body = self._queue.get(timeout=60)
            except queue.Empty:
                return                                   # nothing to do for a minute: the thread ends, a new one starts when needed
            msg = self._message(to, subject, body)
            for attempt in range(len(self.retry_delays) + 1):
                try:
                    self._deliver(msg)
                    entry["state"], entry["error"] = "sent", None
                    self.sent += 1
                    break
                except Exception as e:                    # a mail server can fail in many ways; none may stop the worker
                    last = attempt >= len(self.retry_delays)
                    entry["state"], entry["error"] = ("failed" if last else "retrying"), f"{type(e).__name__}: {e}"[:200]
                    logger.warning("mail to %s failed (attempt %d): %s", to, attempt + 1, e)
                    if last:
                        self.failed += 1
                    else:
                        time.sleep(self.retry_delays[attempt])

    def drain(self, timeout=10.0):
        """Wait until the queue is empty (tests)."""
        end = time.time() + timeout
        while time.time() < end and (not self._queue.empty() or any(x["state"] in ("queued", "retrying") for x in self.log)):
            time.sleep(0.02)
