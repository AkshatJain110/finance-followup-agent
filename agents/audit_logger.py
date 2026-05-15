"""
agents/audit_logger.py
───────────────────────
Appends structured audit records to logs/emails_log.json
and escalated accounts to logs/escalated_accounts.json.
"""

import os
from datetime import datetime

from utils.helpers import load_json_file, save_json_file

# ── File paths ───────────────────────────────────────────────────────────────

LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
EMAIL_LOG_PATH = os.path.join(LOGS_DIR, "emails_log.json")
ESCALATED_LOG_PATH = os.path.join(LOGS_DIR, "escalated_accounts.json")


def log_email_sent(
    invoice_no: str,
    client_name: str,
    overdue_days: int,
    stage: int,
    tone: str,
    subject: str,
    send_status: str,
    email_body: str,
) -> dict:
    """Append a new audit record to emails_log.json and return the record."""
    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "invoice_no": invoice_no,
        "client_name": client_name,
        "overdue_days": overdue_days,
        "escalation_stage": stage,
        "tone_used": tone,
        "email_subject": subject,
        "send_status": send_status,
        "email_body": email_body,
    }

    existing = load_json_file(EMAIL_LOG_PATH)
    existing.append(record)
    save_json_file(EMAIL_LOG_PATH, existing)

    return record


def log_escalated_account(
    invoice_no: str,
    client_name: str,
    amount_due: float,
    overdue_days: int,
    contact_email: str,
) -> dict:
    """Append a Stage-5 (>30 days overdue) record to escalated_accounts.json."""
    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "invoice_no": invoice_no,
        "client_name": client_name,
        "amount_due": amount_due,
        "overdue_days": overdue_days,
        "contact_email": contact_email,
        "status": "Flagged for Legal/Manual Finance Review",
    }

    existing = load_json_file(ESCALATED_LOG_PATH)

    # Avoid duplicate entries for the same invoice in the same run
    existing = [e for e in existing if e.get("invoice_no") != invoice_no]
    existing.append(record)
    save_json_file(ESCALATED_LOG_PATH, existing)

    return record
