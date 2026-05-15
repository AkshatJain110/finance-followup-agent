"""
agents/invoice_processor.py
────────────────────────────
Orchestrates the full pipeline:
  1. Read CSV
  2. Detect overdue invoices
  3. Determine escalation stage
  4. Generate emails (or flag for review)
  5. Log everything

This is the main "agent" function called by app.py.
"""

import os
import pandas as pd

from agents.escalation_engine import get_escalation
from agents.email_generator import generate_email
from agents.audit_logger import log_email_sent, log_escalated_account
from utils.helpers import calculate_overdue_days

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "invoices.csv")


def load_invoices(csv_path: str = DATA_PATH) -> pd.DataFrame:
    """Read and validate the invoices CSV.

    Returns a DataFrame with normalised column names and dtypes.
    """
    required_cols = {
        "invoice_no", "client_name", "amount_due",
        "due_date", "contact_email", "followup_count", "payment_link"
    }
    df = pd.read_csv(csv_path)
    df.columns = [c.strip().lower() for c in df.columns]

    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")

    df["amount_due"] = pd.to_numeric(df["amount_due"], errors="coerce").fillna(0.0)
    df["followup_count"] = pd.to_numeric(df["followup_count"], errors="coerce").fillna(0).astype(int)

    return df


def run_agent(csv_path: str = DATA_PATH) -> dict:
    """
    Main pipeline function. Processes all invoices in the CSV.

    Returns a summary dict:
    {
        "total": int,
        "overdue": int,
        "emails_generated": int,
        "escalated": int,
        "results": [ { ...per-invoice result... } ]
    }
    """
    df = load_invoices(csv_path)
    total = len(df)

    results = []
    overdue_count = 0
    emails_generated = 0
    escalated_count = 0

    for _, row in df.iterrows():
        invoice_no   = str(row["invoice_no"]).strip()
        client_name  = str(row["client_name"]).strip()
        amount_due   = float(row["amount_due"])
        due_date     = str(row["due_date"]).strip()
        contact_email = str(row["contact_email"]).strip()
        followup_count = int(row["followup_count"])
        payment_link = str(row["payment_link"]).strip()

        overdue_days = calculate_overdue_days(due_date)

        # Skip invoices that are not yet overdue
        if overdue_days <= 0:
            results.append({
                "invoice_no": invoice_no,
                "client_name": client_name,
                "overdue_days": 0,
                "status": "Not Overdue — Skipped",
                "stage": None,
                "tone": None,
                "subject": None,
                "body": None,
                "send_status": "skipped",
            })
            continue

        overdue_count += 1
        escalation = get_escalation(overdue_days)

        # ── Stage 5: Flag for legal review, do NOT generate email ────────────
        if escalation.flag_for_review:
            escalated_count += 1
            log_escalated_account(
                invoice_no=invoice_no,
                client_name=client_name,
                amount_due=amount_due,
                overdue_days=overdue_days,
                contact_email=contact_email,
            )
            results.append({
                "invoice_no": invoice_no,
                "client_name": client_name,
                "overdue_days": overdue_days,
                "status": "Escalated — Flagged for Legal/Manual Review",
                "stage": escalation.stage,
                "tone": escalation.tone,
                "subject": None,
                "body": None,
                "send_status": "escalated",
            })
            continue

        # ── Stages 1–4: Generate & (dry-run) send email ──────────────────────
        try:
            email_data = generate_email(
                client_name=client_name,
                invoice_no=invoice_no,
                amount_due=amount_due,
                due_date=due_date,
                overdue_days=overdue_days,
                payment_link=payment_link,
                stage=escalation.stage,
                tone=escalation.tone,
            )
            send_status = "dry-run: sent"
            emails_generated += 1

        except EnvironmentError as env_err:
            # API key not configured — use a placeholder email for demo
            email_data = _demo_email(
                client_name=client_name,
                invoice_no=invoice_no,
                amount_due=amount_due,
                overdue_days=overdue_days,
                payment_link=payment_link,
                stage=escalation.stage,
                tone=escalation.tone,
            )
            send_status = f"dry-run: demo (no API key)"
            emails_generated += 1

        except Exception as exc:
            email_data = {"subject": "Error generating email", "body": str(exc)}
            send_status = f"error: {str(exc)[:80]}"

        # ── Audit log ────────────────────────────────────────────────────────
        log_email_sent(
            invoice_no=invoice_no,
            client_name=client_name,
            overdue_days=overdue_days,
            stage=escalation.stage,
            tone=escalation.tone,
            subject=email_data["subject"],
            send_status=send_status,
            email_body=email_data["body"],
        )

        results.append({
            "invoice_no": invoice_no,
            "client_name": client_name,
            "overdue_days": overdue_days,
            "amount_due": amount_due,
            "contact_email": contact_email,
            "status": "Email Generated",
            "stage": escalation.stage,
            "tone": escalation.tone,
            "subject": email_data["subject"],
            "body": email_data["body"],
            "send_status": send_status,
        })

    return {
        "total": total,
        "overdue": overdue_count,
        "emails_generated": emails_generated,
        "escalated": escalated_count,
        "results": results,
    }


# ── Demo email fallback (used when OPENAI_API_KEY is not configured) ─────────

def _demo_email(
    client_name, invoice_no, amount_due, overdue_days,
    payment_link, stage, tone
) -> dict:
    """Generate a realistic-looking template email without calling the API.
    Used in demo / no-key scenarios so the UI is still functional."""

    tone_intros = {
        1: (
            f"I hope this message finds you well! We wanted to send a quick, "
            f"friendly reminder that invoice {invoice_no} for ${amount_due:,.2f} "
            f"was due {overdue_days} day(s) ago."
        ),
        2: (
            f"We are writing to inform you that invoice {invoice_no} for "
            f"${amount_due:,.2f} is now {overdue_days} days overdue. We kindly "
            f"request you arrange payment at your earliest convenience."
        ),
        3: (
            f"Please be advised that invoice {invoice_no} for ${amount_due:,.2f} "
            f"remains outstanding and is now {overdue_days} days past its due date. "
            f"Immediate settlement is required to avoid further action."
        ),
        4: (
            f"This is an urgent notice regarding invoice {invoice_no} for "
            f"${amount_due:,.2f}, which is now {overdue_days} days overdue. "
            f"Failure to pay immediately may result in escalation to our legal team."
        ),
    }

    subjects = {
        1: f"Friendly Reminder: Invoice {invoice_no} Payment",
        2: f"Action Required: Invoice {invoice_no} Overdue",
        3: f"Formal Notice: Invoice {invoice_no} — {overdue_days} Days Outstanding",
        4: f"URGENT: Immediate Payment Required — Invoice {invoice_no}",
    }

    intro = tone_intros.get(stage, tone_intros[2])
    subject = subjects.get(stage, f"Follow-Up: Invoice {invoice_no}")

    body = f"""Dear {client_name},

{intro}

Please use the link below to complete your payment immediately:
{payment_link}

If you have already made this payment, please disregard this notice and send us the payment confirmation.

If you are experiencing any difficulties or wish to discuss payment arrangements, do not hesitate to contact our finance team.

Thank you for your prompt attention to this matter.

Warm regards,
Finance Collections Team"""

    return {"subject": subject, "body": body}
