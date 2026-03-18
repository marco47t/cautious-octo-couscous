import imaplib, smtplib, email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header as _dh
from config import EMAIL_ADDRESS, EMAIL_APP_PASSWORD
from utils.logger import logger

IMAP = "imap.gmail.com"
SMTP, SMTP_PORT = "smtp.gmail.com", 587

def _decode(val):
    if not val:
        return ""
    raw, enc = _dh(val)[0]
    return raw.decode(enc or "utf-8", errors="replace") if isinstance(raw, bytes) else raw

def read_emails(count: int = 5) -> str:
    """Read the latest emails from the inbox.

    Args:
        count: Number of recent emails to return (default 5).

    Returns:
        Formatted email summaries.
    """
    try:
        m = imaplib.IMAP4_SSL(IMAP)
        m.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        m.select("INBOX")
        _, data = m.search(None, "ALL")
        ids = data[0].split()[-count:]
        out = f"Last {len(ids)} emails:\n\n"
        for eid in reversed(ids):
            _, msg_data = m.fetch(eid, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            out += f"📧 {_decode(msg['Subject'])}\n   From: {_decode(msg['From'])}\n   {msg['Date']}\n\n"
        m.logout()
        return out
    except Exception as e:
        return f"Failed to read emails: {e}"

def send_email(to: str, subject: str, body: str) -> str:
    """Send an email on behalf of the user.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain text email body.

    Returns:
        Confirmation or error message.
    """
    try:
        msg = MIMEMultipart()
        msg["From"], msg["To"], msg["Subject"] = EMAIL_ADDRESS, to, subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(SMTP, SMTP_PORT) as s:
            s.starttls()
            s.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            s.send_message(msg)
        return f"✅ Email sent to {to}"
    except Exception as e:
        return f"Failed to send email: {e}"

def search_emails(keyword: str, count: int = 10) -> str:
    """Search inbox emails by keyword in the subject.

    Args:
        keyword: Word or phrase to search for in email subjects.
        count: Max number of results (default 10).

    Returns:
        Matching email summaries.
    """
    try:
        m = imaplib.IMAP4_SSL(IMAP)
        m.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        m.select("INBOX")
        _, data = m.search(None, f'SUBJECT "{keyword}"')
        ids = data[0].split()[-count:]
        if not ids:
            return f"No emails found for: '{keyword}'"
        out = f"Emails matching '{keyword}':\n\n"
        for eid in reversed(ids):
            _, msg_data = m.fetch(eid, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            out += f"📧 {_decode(msg['Subject'])} — {_decode(msg['From'])}\n"
        m.logout()
        return out
    except Exception as e:
        return f"Email search failed: {e}"
