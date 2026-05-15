"""
app.py
Finance Follow-Up Email Agent — Streamlit Dashboard
Run with: streamlit run app.py
"""

import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from agents.invoice_processor import run_agent, load_invoices
from utils.helpers import calculate_overdue_days, load_json_file

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Finance Follow-Up Agent",
    page_icon="📬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS — clean white minimal ─────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

/* ── Hide Streamlit's default top bar (Deploy + 3-dot menu) ── */
header[data-testid="stHeader"]          { display: none !important; }
#MainMenu                               { display: none !important; }
.stDeployButton                         { display: none !important; }
footer                                  { display: none !important; }
div[data-testid="stToolbar"]            { display: none !important; }
div[data-testid="stDecoration"]         { display: none !important; }

/* Fix top padding now that header is gone */
.block-container { padding-top: 1.8rem !important; }

*, html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    box-sizing: border-box;
}

/* White background everywhere */
.stApp, .main, section[data-testid="stSidebar"] > div {
    background-color: #ffffff !important;
}

/* Remove default streamlit padding weirdness */
.block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1100px; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    border-right: 1px solid #e5e7eb;
    background: #fafafa !important;
}
section[data-testid="stSidebar"] > div { background: #fafafa !important; }

/* ── Typography ── */
.page-title {
    font-size: 1.45rem;
    font-weight: 600;
    color: #111827;
    margin-bottom: 2px;
    letter-spacing: -0.3px;
}
.page-subtitle {
    font-size: 0.875rem;
    color: #6b7280;
    margin-bottom: 1.5rem;
}
.section-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: #9ca3af;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 0.75rem;
    margin-top: 1.5rem;
}

/* ── Stat cards ── */
.stat-row { display: flex; gap: 12px; margin-bottom: 1.5rem; }
.stat-card {
    flex: 1;
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 18px 20px;
}
.stat-card .s-label {
    font-size: 0.75rem;
    color: #6b7280;
    font-weight: 500;
    margin-bottom: 6px;
}
.stat-card .s-value {
    font-size: 1.9rem;
    font-weight: 600;
    color: #111827;
    line-height: 1;
}
.stat-card .s-sub {
    font-size: 0.72rem;
    color: #9ca3af;
    margin-top: 4px;
}
.stat-card.warn .s-value { color: #d97706; }
.stat-card.ok   .s-value { color: #059669; }
.stat-card.danger .s-value { color: #dc2626; }

/* ── Badge / pill ── */
.pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 99px;
    font-size: 0.72rem;
    font-weight: 500;
}
.pill-blue   { background:#eff6ff; color:#2563eb; border:1px solid #bfdbfe; }
.pill-green  { background:#f0fdf4; color:#15803d; border:1px solid #bbf7d0; }
.pill-yellow { background:#fffbeb; color:#b45309; border:1px solid #fde68a; }
.pill-red    { background:#fff1f2; color:#be123c; border:1px solid #fecdd3; }
.pill-gray   { background:#f9fafb; color:#374151; border:1px solid #e5e7eb; }
.pill-sent   { background:#f0fdf4; color:#15803d; border:1px solid #bbf7d0; }

/* ── Email card ── */
.email-card {
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 8px;
    background: #ffffff;
}
.email-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 4px;
}
.email-card-title {
    font-size: 0.875rem;
    font-weight: 600;
    color: #111827;
}
.email-card-meta {
    font-size: 0.78rem;
    color: #6b7280;
    margin-bottom: 10px;
}
.email-subject {
    font-size: 0.8rem;
    font-weight: 500;
    color: #374151;
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 8px 12px;
    margin-bottom: 10px;
}
.email-body-box {
    font-size: 0.8rem;
    color: #374151;
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-left: 3px solid #d1d5db;
    border-radius: 0 6px 6px 0;
    padding: 12px 16px;
    white-space: pre-wrap;
    line-height: 1.6;
}

/* ── Escalated card ── */
.esc-card {
    border: 1px solid #fecaca;
    border-radius: 10px;
    padding: 14px 18px;
    background: #fff1f2;
    margin-bottom: 8px;
}
.esc-card-title { font-size: 0.875rem; font-weight: 600; color: #991b1b; }
.esc-card-meta  { font-size: 0.78rem; color: #b91c1c; margin-top: 2px; }

/* ── Button ── */
.stButton > button {
    background: #111827;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s;
}
.stButton > button:hover { background: #1f2937; }

/* ── Expander cleanup ── */
div[data-testid="stExpander"] {
    border: 1px solid #e5e7eb !important;
    border-radius: 10px !important;
    background: #ffffff !important;
    box-shadow: none !important;
}
div[data-testid="stExpander"] summary {
    font-size: 0.875rem;
    font-weight: 500;
    color: #111827;
}

/* ── Divider ── */
hr { border: none; border-top: 1px solid #f3f4f6; margin: 1.5rem 0; }

/* ── Table ── */
.stDataFrame { border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; }

/* ── Alerts ── */
.stAlert { border-radius: 8px !important; }

/* ── Input ── */
.stTextInput input {
    border: 1px solid #e5e7eb;
    border-radius: 7px;
    font-size: 0.875rem;
    background: #ffffff;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("**Finance Agent**")
    st.markdown("<hr style='border-top:1px solid #e5e7eb;margin:0.5rem 0 1rem'>", unsafe_allow_html=True)

    csv_path = st.text_input("CSV file path", value="data/invoices.csv")

    st.markdown("<div class='section-label'>Escalation Stages</div>", unsafe_allow_html=True)
    stages = [
        ("1", "1–7 days",   "Warm & Friendly",   "pill-blue"),
        ("2", "8–14 days",  "Polite but Firm",   "pill-green"),
        ("3", "15–21 days", "Formal & Serious",  "pill-yellow"),
        ("4", "22–30 days", "Stern & Urgent",    "pill-red"),
        ("5", ">30 days",   "Legal Review",      "pill-gray"),
    ]
    for stage, days, tone, pill in stages:
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:6px'>"
            f"<span style='font-size:0.75rem;color:#6b7280;width:60px'>{days}</span>"
            f"<span class='pill {pill}'>{tone}</span></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<hr style='border-top:1px solid #e5e7eb;margin:1rem 0'>", unsafe_allow_html=True)

    api_key_ok = (
        bool(os.getenv("OPENAI_API_KEY", "").strip())
        and not os.getenv("OPENAI_API_KEY", "").startswith("sk-your")
    )
    if api_key_ok:
        st.markdown(
            "<span class='pill pill-green'>API key active</span>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<span class='pill pill-yellow'>Demo mode — no API key</span>",
            unsafe_allow_html=True,
        )

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("<div class='page-title'>Finance Follow-Up Agent</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='page-subtitle'>Detects overdue invoices and generates personalized follow-up emails automatically.</div>",
    unsafe_allow_html=True,
)

# ── Invoice table ─────────────────────────────────────────────────────────────

st.markdown("<div class='section-label'>Invoice Overview</div>", unsafe_allow_html=True)

try:
    df_preview = load_invoices(csv_path)
    df_preview["overdue_days"] = df_preview["due_date"].apply(
        lambda d: calculate_overdue_days(str(d))
    )

    def status_label(d):
        if d <= 0:   return "Not due"
        if d > 30:   return f"Escalated ({d}d)"
        return f"{d}d overdue"

    df_preview["status"] = df_preview["overdue_days"].apply(status_label)

    st.dataframe(
        df_preview[["invoice_no", "client_name", "amount_due", "due_date", "overdue_days", "status"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "invoice_no":   st.column_config.TextColumn("Invoice"),
            "client_name":  st.column_config.TextColumn("Client"),
            "amount_due":   st.column_config.NumberColumn("Amount Due", format="$%.2f"),
            "due_date":     st.column_config.TextColumn("Due Date"),
            "overdue_days": st.column_config.NumberColumn("Days Overdue"),
            "status":       st.column_config.TextColumn("Status"),
        },
    )

except FileNotFoundError:
    st.error(f"CSV not found: `{csv_path}`")
    st.stop()
except ValueError as e:
    st.error(f"CSV format error: {e}")
    st.stop()

st.markdown("<hr>", unsafe_allow_html=True)

# ── Run button ────────────────────────────────────────────────────────────────

col_btn, col_note = st.columns([1, 4])
with col_btn:
    run_clicked = st.button("Run Agent", use_container_width=True)
with col_note:
    st.markdown(
        "<p style='font-size:0.8rem;color:#9ca3af;margin-top:10px'>"
        "Processes overdue invoices, generates emails, and writes audit logs. No real emails are sent.</p>",
        unsafe_allow_html=True,
    )

# ── Results ───────────────────────────────────────────────────────────────────

if run_clicked:
    with st.spinner("Running…"):
        try:
            summary = run_agent(csv_path)
        except Exception as e:
            st.error(f"Agent error: {e}")
            st.stop()

    # ── Stats ─────────────────────────────────────────────────────────────────
    st.markdown("<div class='section-label'>Summary</div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)

    def stat(col, label, val, sub, cls=""):
        with col:
            st.markdown(
                f"<div class='stat-card {cls}'>"
                f"<div class='s-label'>{label}</div>"
                f"<div class='s-value'>{val}</div>"
                f"<div class='s-sub'>{sub}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    stat(c1, "Total Invoices",    summary["total"],            "in file")
    stat(c2, "Overdue",           summary["overdue"],          "need action",      "warn")
    stat(c3, "Emails Generated",  summary["emails_generated"], "dry-run complete", "ok")
    stat(c4, "Escalated",         summary["escalated"],        ">30 days",         "danger")

    # ── Emails ────────────────────────────────────────────────────────────────
    emailed   = [r for r in summary["results"] if r["send_status"] not in ("skipped", "escalated")]
    escalated = [r for r in summary["results"] if r["send_status"] == "escalated"]
    skipped   = [r for r in summary["results"] if r["send_status"] == "skipped"]

    stage_pill = {1: "pill-blue", 2: "pill-green", 3: "pill-yellow", 4: "pill-red"}

    if emailed:
        st.markdown("<div class='section-label'>Generated Emails</div>", unsafe_allow_html=True)
        for r in emailed:
            pill_cls = stage_pill.get(r["stage"], "pill-gray")
            label = f"{r['invoice_no']} — {r['client_name']}"
            with st.expander(label):
                # Meta row
                mc1, mc2, mc3 = st.columns([2, 1, 1])
                mc1.markdown(
                    f"<div style='font-size:0.8rem;color:#6b7280'>{r['client_name']}</div>",
                    unsafe_allow_html=True,
                )
                mc2.markdown(
                    f"<div style='font-size:0.8rem;color:#6b7280'>${r.get('amount_due', 0):,.2f}</div>",
                    unsafe_allow_html=True,
                )
                mc3.markdown(
                    f"<span class='pill {pill_cls}'>Stage {r['stage']} · {r['overdue_days']}d overdue</span>",
                    unsafe_allow_html=True,
                )

                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

                # Subject
                st.markdown(
                    f"<div style='font-size:0.72rem;color:#9ca3af;margin-bottom:4px'>Subject</div>"
                    f"<div class='email-subject'>{r['subject']}</div>",
                    unsafe_allow_html=True,
                )

                # Body
                st.markdown(
                    f"<div style='font-size:0.72rem;color:#9ca3af;margin-bottom:4px'>Email Body</div>"
                    f"<div class='email-body-box'>{r['body']}</div>",
                    unsafe_allow_html=True,
                )

                # Status
                st.markdown(
                    f"<div style='margin-top:10px'>"
                    f"<span class='pill pill-sent'>Sent (dry-run)</span>"
                    f"&nbsp;<span style='font-size:0.72rem;color:#9ca3af'>{r['contact_email'] if 'contact_email' in r else ''}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── Escalated ─────────────────────────────────────────────────────────────
    if escalated:
        st.markdown("<div class='section-label'>Escalated — Legal Review Required</div>", unsafe_allow_html=True)
        for r in escalated:
            st.markdown(
                f"<div class='esc-card'>"
                f"<div class='esc-card-title'>{r['invoice_no']} — {r['client_name']}</div>"
                f"<div class='esc-card-meta'>"
                f"{r['overdue_days']} days overdue · No email sent · Flagged for manual review"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ── Skipped ───────────────────────────────────────────────────────────────
    if skipped:
        st.markdown("<div class='section-label'>Not Overdue — Skipped</div>", unsafe_allow_html=True)
        rows = "".join(
            f"<div style='font-size:0.8rem;color:#6b7280;padding:4px 0;border-bottom:1px solid #f3f4f6'>"
            f"{r['invoice_no']} &nbsp;·&nbsp; {r['client_name']}</div>"
            for r in skipped
        )
        st.markdown(f"<div style='border:1px solid #e5e7eb;border-radius:8px;padding:8px 14px'>{rows}</div>", unsafe_allow_html=True)

    # ── Audit log ─────────────────────────────────────────────────────────────
    st.markdown("<div class='section-label'>Audit Log</div>", unsafe_allow_html=True)

    email_log_path = os.path.join("logs", "emails_log.json")
    if os.path.exists(email_log_path):
        log_data = load_json_file(email_log_path)
        if log_data:
            log_df = pd.DataFrame(log_data)[
                ["timestamp", "invoice_no", "client_name", "overdue_days",
                 "escalation_stage", "tone_used", "email_subject", "send_status"]
            ]
            st.dataframe(log_df, use_container_width=True, hide_index=True)
        else:
            st.markdown(
                "<p style='font-size:0.8rem;color:#9ca3af'>No log entries yet.</p>",
                unsafe_allow_html=True,
            )

    st.markdown(
        "<p style='font-size:0.75rem;color:#9ca3af;margin-top:8px'>"
        "Logs saved to <code>logs/emails_log.json</code> and <code>logs/escalated_accounts.json</code></p>",
        unsafe_allow_html=True,
    )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<p style='font-size:0.72rem;color:#d1d5db;text-align:center'>"
    "Finance Follow-Up Agent · LangChain + GPT-4o-mini · Dry-run mode"
    "</p>",
    unsafe_allow_html=True,
)
