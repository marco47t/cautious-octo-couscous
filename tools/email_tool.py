import imaplib, smtplib, email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header as _dh
from email import policy
from config import EMAIL_ADDRESS, EMAIL_APP_PASSWORD
from utils.logger import logger
from utils.tool_logger import logged_tool

IMAP = "imap.gmail.com"
SMTP, SMTP_PORT = "smtp.gmail.com", 587

def _decode(val):
    if not val:
        return ""
    raw, enc = _dh(val)[0]
    return raw.decode(enc or "utf-8", errors="replace") if isinstance(raw, bytes) else raw

def _extract_body(msg: email.message.Message) -> str:
    """Extract plain text body from an email message, handling multipart."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                try:
                    charset = part.get_content_charset() or "utf-8"
                    body = part.get_payload(decode=True).decode(charset, errors="replace")
                    break
                except Exception:
                    continue
            # Fallback to HTML if no plain text found
            elif ct == "text/html" and "attachment" not in cd and not body:
                try:
                    import re, html
                    charset = part.get_content_charset() or "utf-8"
                    raw_html = part.get_payload(decode=True).decode(charset, errors="replace")
                    body = html.unescape(re.sub(r"<[^>]+>", " ", raw_html))
                    body = re.sub(r"\s{2,}", " ", body).strip()
                except Exception:
                    continue
    else:
        try:
            charset = msg.get_content_charset() or "utf-8"
            body = msg.get_payload(decode=True).decode(charset, errors="replace")
        except Exception:
            body = str(msg.get_payload())
    return body.strip()

def _connect() -> imaplib.IMAP4_SSL:
    m = imaplib.IMAP4_SSL(IMAP)
    m.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
    return m

@logged_tool
def read_emails(count: int = 5) -> str:
    """Read the latest emails from the inbox including full body content.

    Args:
        count: Number of recent emails to return (default 5).

    Returns:
        Formatted email summaries with full body text.
    """
    try:
        m = _connect()
        m.select("INBOX")
        _, data = m.search(None, "ALL")
        ids = data[0].split()[-count:]
        out = f"📬 Last {len(ids)} emails:\n\n"
        for eid in reversed(ids):
            _, msg_data = m.fetch(eid, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            subject = _decode(msg["Subject"])
            sender  = _decode(msg["From"])
            date    = msg.get("Date", "")[:25]
            body    = _extract_body(msg)
            preview = body[:500] + ("..." if len(body) > 500 else "")
            out += (
                f"{'─'*40}\n"
                f"📧 {subject}\n"
                f"👤 From: {sender}\n"
                f"📅 {date}\n\n"
                f"{preview}\n\n"
            )
        m.logout()
        return out
    except Exception as e:
        return f"Failed to read emails: {e}"

@logged_tool
def open_email(email_index: int) -> str:
    """Open and read the full content of a specific email by its position in the inbox.
    Email index 1 = most recent, 2 = second most recent, etc.

    Args:
        email_index: Position of the email (1 = most recent).

    Returns:
        Full email content including all headers and body.
    """
    try:
        m = _connect()
        m.select("INBOX")
        _, data = m.search(None, "ALL")
        all_ids = data[0].split()
        if not all_ids:
            return "Inbox is empty."

        # Index 1 = most recent = last in list
        idx = len(all_ids) - email_index
        if idx < 0 or idx >= len(all_ids):
            return f"Email index {email_index} out of range (inbox has {len(all_ids)} emails)."

        eid = all_ids[idx]
        _, msg_data = m.fetch(eid, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])

        subject = _decode(msg["Subject"])
        sender  = _decode(msg["From"])
        to      = _decode(msg["To"])
        date    = msg.get("Date", "")
        body    = _extract_body(msg)

        # List attachments
        attachments = []
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                fname = part.get_filename()
                if fname:
                    attachments.append(_decode(fname))

        out = (
            f"📧 **{subject}**\n\n"
            f"👤 From: {sender}\n"
            f"📨 To: {to}\n"
            f"📅 Date: {date}\n"
        )
        if attachments:
            out += f"📎 Attachments: {', '.join(attachments)}\n"
        out += f"\n{'─'*40}\n\n{body[:3000]}"
        if len(body) > 3000:
            out += f"\n\n[Truncated — {len(body)} total chars]"

        m.logout()
        return out
    except Exception as e:
        return f"Failed to open email: {e}"

@logged_tool
def search_emails(keyword: str, count: int = 10) -> str:
    """Search inbox emails by keyword in subject or body.

    Args:
        keyword: Word or phrase to search for.
        count: Max number of results (default 10).

    Returns:
        Matching email summaries with body preview.
    """
    try:
        m = _connect()
        m.select("INBOX")
        _, data = m.search(None, f'TEXT "{keyword}"')  # search body + subject
        ids = data[0].split()[-count:]
        if not ids:
            return f"No emails found matching: '{keyword}'"
        out = f"🔍 Emails matching '{keyword}':\n\n"
        for eid in reversed(ids):
            _, msg_data = m.fetch(eid, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            subject = _decode(msg["Subject"])
            sender  = _decode(msg["From"])
            body    = _extract_body(msg)
            preview = body[:200] + "..." if len(body) > 200 else body
            out += f"📧 **{subject}**\n   From: {sender}\n   {preview}\n\n"
        m.logout()
        return out
    except Exception as e:
        return f"Email search failed: {e}"

def _send_email_direct(to: str, subject: str, body: str) -> str:
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

@logged_tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email — requires user confirmation before sending.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain text email body.

    Returns:
        Confirmation request with action ID.
    """
    from bot.confirmation import register_action
    action_id = register_action(
        func=_send_email_direct,
        args={"to": to, "subject": subject, "body": body},
        description=f"Send email to {to} — Subject: {subject}"
    )
    return (
        f"📧 Ready to send email:\n"
        f"**To:** {to}\n"
        f"**Subject:** {subject}\n"
        f"**Preview:** {body[:150]}{'...' if len(body) > 150 else ''}\n\n"
        f"CONFIRM_ID:{action_id}"
    )
