"""
Development email backend: prints each email as readable plain text.

Django's console backend prints the raw MIME message (quoted-printable
=20 / =3D codes, HTML markup, both text and HTML copies). This backend prints
only what a person would read: recipient, subject and the plain-text body,
including temporary passwords and sign-in links.

Enable with:  EMAIL_BACKEND=kyisa_cms.dev_email_backend.EmailBackend
Development only: never use in production.
"""
import sys
import threading

from django.core.mail.backends.base import BaseEmailBackend

_lock = threading.Lock()
_RULE = "-" * 72


def _readable_body(message):
    """Plain-text body; converts HTML if that's all the message has."""
    from kyisa_cms.email_utils import html_to_text

    body = (message.body or "").strip()
    if body and "<" not in body[:200]:
        return body
    html_body = next(
        (content for content, mimetype in getattr(message, "alternatives", []) if mimetype == "text/html"),
        body,
    )
    return html_to_text(html_body).strip()


class EmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages or []:
            try:
                self._print(message)
                sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return sent

    def _print(self, message):
        text = (
            f"\n{_RULE}\n"
            f"EMAIL (development, not sent)\n"
            f"To:      {', '.join(message.recipients())}\n"
            f"Subject: {message.subject}\n"
            f"{_RULE}\n"
            f"{_readable_body(message)}\n"
            f"{_RULE}\n"
        )
        stream = sys.stdout
        encoding = getattr(stream, "encoding", None) or "utf-8"
        with _lock:
            # Windows consoles (cp1252) can't print every character; never let
            # printing fail the send.
            stream.write(text.encode(encoding, "replace").decode(encoding, "replace"))
            stream.flush()
