"""Private verification delivery; preview messages never become public API responses."""

import os
import secrets
import smtplib
import ssl
from email.message import EmailMessage

from studio.settings import SERVER_DIR


class MailUnavailable(Exception):
    pass


def send_verification(settings, recipient: str, code: str):
    message = EmailMessage()
    message["Subject"] = "Handbalancer's Studio - код підтвердження"
    message["From"] = settings.smtp_from or "studio@localhost"
    message["To"] = recipient
    message.set_content(
        f"Ваш код підтвердження: {code}\n\nКод діє 10 хвилин. "
        "Якщо ви не реєструвались, проігноруйте цей лист."
    )
    if settings.smtp_host and settings.smtp_from:
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException):
            raise MailUnavailable() from None
    elif settings.preview_enabled:
        inbox = SERVER_DIR.parent / ".local-tools" / "mail-inbox"
        inbox.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(inbox, 0o700)
        path = inbox / f"{secrets.token_hex(16)}.eml"
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as output:
            output.write(message.as_bytes())
    else:
        raise MailUnavailable()
