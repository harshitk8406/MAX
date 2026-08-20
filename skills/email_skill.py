"""
MAX 2.0 — Email Skill
Full Gmail integration: read inbox, search emails, compose & send.
Requires Gmail App Password in config.json.
"""
import json
import os
import imaplib
import email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from skills.router import skill
from core.logger import log

_cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
with open(_cfg_path) as f:
    _cfg = json.load(f)

_EMAIL_CFG = _cfg.get("email", {})
_ADDRESS   = _EMAIL_CFG.get("address", "")
_PASSWORD  = _EMAIL_CFG.get("password", "")
_RECIPIENT = _EMAIL_CFG.get("default_recipient", "")

_NOT_CONFIGURED = (
    not _ADDRESS or _ADDRESS == "your_email@gmail.com" or
    not _PASSWORD or _PASSWORD == "your_app_password_here"
)


def _imap_connect():
    """Connect to Gmail IMAP. Returns mail object or None."""
    if _NOT_CONFIGURED:
        return None
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(_ADDRESS, _PASSWORD)
        return mail
    except Exception as e:
        log.error(f"IMAP connect error: {e}")
        return None


def _parse_email(msg) -> dict:
    """Extract subject, sender, date, and body snippet from email."""
    subject = email.header.decode_header(msg["Subject"])[0]
    subject = subject[0].decode(subject[1] or "utf-8") if isinstance(subject[0], bytes) else subject[0]
    sender  = msg.get("From", "")
    date    = msg.get("Date", "")[:25]

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode("utf-8", errors="replace")[:300]
                except Exception:
                    pass
                break
    else:
        try:
            body = msg.get_payload(decode=True).decode("utf-8", errors="replace")[:300]
        except Exception:
            pass

    return {"subject": subject, "sender": sender, "date": date, "body": body.strip()}


@skill("read_email")
def read_email(args: dict, spoken: str) -> str:
    """Read the latest unread emails."""
    if _NOT_CONFIGURED:
        return ("Email isn't set up yet. Add your Gmail address and App Password to config.json. "
                "You can generate an App Password at myaccount.google.com/apppasswords")

    count = args.get("count", 3)
    mail = _imap_connect()
    if not mail:
        return "Couldn't connect to Gmail. Check your credentials."

    try:
        mail.select("INBOX")
        _, data = mail.search(None, "UNSEEN")
        ids = data[0].split()

        if not ids:
            mail.logout()
            return spoken or "Your inbox is clean! No unread emails."

        # Fetch latest N unread
        recent_ids = ids[-int(count):]
        emails = []
        for eid in reversed(recent_ids):
            _, msg_data = mail.fetch(eid, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            emails.append(_parse_email(msg))

        mail.logout()

        if len(emails) == 1:
            e = emails[0]
            return (spoken or
                    f"You have 1 unread email from {e['sender']}: '{e['subject']}'. "
                    f"Message preview: {e['body'][:100]}")

        summary_parts = [f"{len(ids)} unread email{'s' if len(ids) > 1 else ''}. Here are the latest:"]
        for i, e in enumerate(emails, 1):
            summary_parts.append(f"{i}: From {e['sender']}, subject: {e['subject']}.")
        return spoken or " ".join(summary_parts)

    except Exception as e:
        log.error(f"Read email error: {e}")
        return f"Couldn't read emails: {e}"


@skill("search_email")
def search_email(args: dict, spoken: str) -> str:
    """Search inbox by sender or subject keyword."""
    if _NOT_CONFIGURED:
        return "Email isn't configured. Add credentials to config.json."

    sender_query = args.get("from", "") or args.get("sender", "")
    subject_query = args.get("subject", "") or args.get("keyword", "") or args.get("about", "")

    mail = _imap_connect()
    if not mail:
        return "Couldn't connect to Gmail."

    try:
        mail.select("INBOX")
        criteria = []
        if sender_query:
            criteria.append(f'FROM "{sender_query}"')
        if subject_query:
            criteria.append(f'SUBJECT "{subject_query}"')
        if not criteria:
            criteria.append("ALL")

        search_str = " ".join(criteria)
        _, data = mail.search(None, search_str)
        ids = data[0].split()

        if not ids:
            mail.logout()
            return spoken or f"No emails found matching your search."

        recent = ids[-3:]
        emails = []
        for eid in reversed(recent):
            _, msg_data = mail.fetch(eid, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            emails.append(_parse_email(msg))

        mail.logout()
        parts = [f"Found {len(ids)} matching email{'s' if len(ids) > 1 else ''}. Latest:"]
        for e in emails:
            parts.append(f"From {e['sender']}, '{e['subject']}'.")
        return spoken or " ".join(parts)

    except Exception as e:
        log.error(f"Search email error: {e}")
        return f"Email search failed: {e}"


@skill("send_email")
def send_email(args: dict, spoken: str) -> str:
    if _NOT_CONFIGURED:
        return ("Email isn't set up. Add your Gmail address and App Password to config.json. "
                "Generate one at myaccount.google.com/apppasswords")

    to = args.get("to", "") or args.get("recipient", "") or _RECIPIENT
    subject = args.get("subject", "Message from MAX")
    body = args.get("body", "") or args.get("content", "") or args.get("message", "")

    if not to:
        from core.voice import take_command
        to = take_command(prompt="Who should I send this to? Say the email address.")
    if not body:
        from core.voice import take_command
        body = take_command(prompt="What should the email say?")
    if not body:
        return "I need a message to send."

    try:
        msg = MIMEMultipart()
        msg["From"]    = _ADDRESS
        msg["To"]      = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(_ADDRESS, _PASSWORD)
            server.sendmail(_ADDRESS, to, msg.as_string())

        log.info(f"Email sent to {to}")
        return spoken or f"Email sent to {to}!"

    except Exception as e:
        log.error(f"Send email error: {e}")
        return f"Couldn't send the email: {e}"
