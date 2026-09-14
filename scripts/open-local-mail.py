"""Open the latest local verification emails without printing their contents."""

import html
import os
import webbrowser
from email import policy
from email.parser import BytesParser
from pathlib import Path

inbox = Path(__file__).resolve().parents[1] / ".local-tools" / "mail-inbox"
messages = sorted(
    inbox.glob("*.eml"), key=lambda path: path.stat().st_mtime, reverse=True
)[:10]
if not messages:
    raise SystemExit(
        "No local verification messages yet. Submit the registration form first."
    )
parts = []
for path in messages:
    mail = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    body = mail.get_body(preferencelist=("plain",))
    parts.append(
        "<article><h2>"
        + html.escape(str(mail["To"]))
        + "</h2><pre>"
        + html.escape(body.get_content() if body else "")
        + "</pre></article>"
    )
page = inbox / "inbox.html"
document = (
    '<!doctype html><html lang="uk"><meta charset="utf-8"><title>Studio - локальна пошта</title><style>body{max-width:760px;margin:50px auto;padding:24px;background:#101310;color:#eee;font:17px system-ui}article{padding:24px;margin:20px 0;border:1px solid #3a4a3c;border-radius:18px}h2{font-size:16px}pre{white-space:pre-wrap;font:inherit;line-height:1.7}</style><h1>Локальна тестова пошта</h1><p>Листи збережені лише на цьому комп’ютері.</p>'
    + "".join(parts)
    + "</html>"
)
fd = os.open(page, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as output:
    output.write(document)
os.chmod(page, 0o600)
webbrowser.open(page.as_uri())
print("Private local inbox opened. No verification codes printed.")
