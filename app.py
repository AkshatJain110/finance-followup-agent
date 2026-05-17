"""
app.py
Finance Follow-Up Email Agent — Streamlit Dashboard
Run with: streamlit run app.py
"""

import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from agents.invoice_processor import run_agent, load_invoices
from utils.helpers import calculate_overdue_days, load_json_file

load_dotenv()

# ── Streamlit Cloud secrets support (safe — no crash when running locally) ────
try:
    if "OPENAI_API_KEY" in st.secrets:
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
except Exception:
    pass  # Running locally — use .env file instead

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Finance Follow-Up Agent",
    page_icon="📬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

*, html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    box-sizing: border-box;
}

/* Hide Streamlit default chrome */
header[data-testid="stHeader"]   { display: none !important; }
#MainMenu                         { display: none !important; }
.stDeployButton                   { display: none !important; }
footer                            { display: none !important; }
div[data-testid="stToolbar"]      { display: none !important; }
div[data-testid="stDecoration"]   { display: none !important; }

.stApp, .main { background-color: #ffffff !important; }
section[data-testid="stSidebar"] > div { background: #fafafa !important; }
section[data-testid="stSidebar"] { border-right: 1px solid #e5e7eb; }

.block-container { padding-top: 1.8rem !important; max-width: 1140px; }

.page-title   { font-size:1.45rem; font-weight:600; color:#111827; letter-spacing:-0.3px; }
.page-sub     { font-size:0.875rem; color:#6b7280; margin-bottom:1.5rem; }
.section-label{
    font-size:0.72rem; font-weight:600; color:#9ca3af;
    letter-spacing:0.07em; text-transform:uppercase;
    margin:1.5rem 0 0.6rem;
}

/* Stat cards */
.stat-card {
    background:#fff; border:1px solid #e5e7eb;
    border-radius:10px; padding:18px 20px;
}
.stat-card .s-label { font-size:0.72rem; color:#6b7280; font-weight:500; margin-bottom:6px; }
.stat-card .s-value { font-size:1.85rem; font-weight:600; color:#111827; line-height:1; }
.stat-card .s-sub   { font-size:0.7rem; color:#9ca3af; margin-top:4px; }
.stat-card.warn  .s-value { color:#d97706; }
.stat-card.ok    .s-value { color:#059669; }
.stat-card.danger.s-value { color:#dc2626; }
.stat-card.info  .s-value { color:#2563eb; }

/* Pills */
.pill { display:inline-block; padding:2px 10px; border-radius:99px; font-size:0.72rem; font-weight:500; }
.pill-blue   { background:#eff6ff; color:#2563eb; border:1px solid #bfdbfe; }
.pill-green  { background:#f0fdf4; color:#15803d; border:1px solid #bbf7d0; }
.pill-yellow { background:#fffbeb; color:#b45309; border:1px solid #fde68a; }
.pill-red    { background:#fff1f2; color:#be123c; border:1px solid #fecdd3; }
.pill-gray   { background:#f9fafb; color:#374151; border:1px solid #e5e7eb; }
.pill-sent   { background:#f0fdf4; color:#15803d; border:1px solid #bbf7d0; }

/* Email cards */
.email-subject {
    font-size:0.8rem; font-weight:500; color:#374151;
    background:#f9fafb; border:1px solid #e5e7eb;
    border-radius:6px; padding:8px 12px; margin-bottom:10px;
}
.email-body-box {
    font-size:0.8rem; color:#374151; background:#f9fafb;
    border:1px solid #e5e7eb; border-left:3px solid #d1d5db;
    border-radius:0 6px 6px 0; padding:12px 16px;
    white-space:pre-wrap; line-height:1.6;
}

/* Escalated card */
.esc-card {
    border:1px solid #fecaca; border-radius:10px;
    padding:14px 18px; background:#fff1f2; margin-bottom:8px;
}
.esc-card-title { font-size:0.875rem; font-weight:600; color:#991b1b; }
.esc-card-meta  { font-size:0.78rem; color:#b91c1c; margin-top:2px; }

/* Pipeline stage boxes */
.pipeline-row { display:flex; gap:8px; margin-bottom:1rem; }
.pipeline-box {
    flex:1; border-radius:8px; padding:14px 16px;
    border:1px solid #e5e7eb; text-align:center;
}
.pipeline-box .p-count { font-size:1.6rem; font-weight:600; line-height:1; }
.pipeline-box .p-label { font-size:0.7rem; color:#6b7280; margin-top:4px; }

/* Button */
.stButton > button {
    background:#111827; color:#fff; border:none;
    border-radius:8px; padding:10px 28px;
    font-size:0.875rem; font-weight:500; transition:background 0.15s;
}
.stButton > button:hover { background:#1f2937; }

div[data-testid="stExpander"] {
    border:1px solid #e5e7eb !important;
    border-radius:10px !important;
    background:#fff !important;
    box-shadow:none !important;
}

hr { border:none; border-top:1px solid #f3f4f6; margin:1.5rem 0; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("**Finance Agent**")
    st.markdown("<hr style='border-top:1px solid #e5e7eb;margin:0.5rem 0 1rem'>", unsafe_allow_html=True)

    csv_path = st.text_input("CSV file path", value="data/invoices.csv")

    st.markdown("<div class='section-label'>Escalation Stages</div>", unsafe_allow_html=True)
    for days, tone, cls in [
        ("1–7 days",   "Warm & Friendly",   "pill-blue"),
        ("8–14 days",  "Polite but Firm",   "pill-green"),
        ("15–21 days", "Formal & Serious",  "pill-yellow"),
        ("22–30 days", "Stern & Urgent",    "pill-red"),
        (">30 days",   "Legal Review",      "pill-gray"),
    ]:
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:6px'>"
            f"<span style='font-size:0.72rem;color:#6b7280;width:66px'>{days}</span>"
            f"<span class='pill {cls}'>{tone}</span></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<hr style='border-top:1px solid #e5e7eb;margin:1rem 0'>", unsafe_allow_html=True)
    api_ok = bool(os.getenv("OPENAI_API_KEY","").strip()) and not os.getenv("OPENAI_API_KEY","").startswith("sk-your")
    st.markdown(
        f"<span class='pill {'pill-green' if api_ok else 'pill-yellow'}'>"
        f"{'API key active' if api_ok else 'Demo mode — no API key'}</span>",
        unsafe_allow_html=True,
    )

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("<div class='page-title'>Finance Follow-Up Agent</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='page-sub'>Detects overdue invoices and generates personalized follow-up emails automatically.</div>",
    unsafe_allow_html=True,
)

# ── Load data ─────────────────────────────────────────────────────────────────
try:
    df = load_invoices(csv_path)
    df["overdue_days"] = df["due_date"].apply(lambda d: calculate_overdue_days(str(d)))
except FileNotFoundError:
    st.error(f"CSV not found: `{csv_path}`")
    st.stop()
except ValueError as e:
    st.error(f"CSV format error: {e}")
    st.stop()

# ── Top KPI row ───────────────────────────────────────────────────────────────
st.markdown("<div class='section-label'>Overview</div>", unsafe_allow_html=True)

overdue_df  = df[df["overdue_days"] > 0]
total       = len(df)
overdue_cnt = len(overdue_df)
escalated   = len(df[df["overdue_days"] > 30])
outstanding = overdue_df["amount_due"].sum()

c1, c2, c3, c4 = st.columns(4)
def stat(col, label, val, sub, cls=""):
    with col:
        st.markdown(
            f"<div class='stat-card {cls}'>"
            f"<div class='s-label'>{label}</div>"
            f"<div class='s-value'>{val}</div>"
            f"<div class='s-sub'>{sub}</div></div>",
            unsafe_allow_html=True,
        )

def indian_format(amount):
    """Format number in Indian currency style: ₹1,23,45,678"""
    amount = int(amount)
    s = str(amount)
    if len(s) <= 3:
        return f"\u20b9{s}"
    last3 = s[-3:]
    rest = s[:-3]
    groups = []
    while len(rest) > 2:
        groups.append(rest[-2:])
        rest = rest[:-2]
    if rest:
        groups.append(rest)
    groups.reverse()
    return f"\u20b9{','.join(groups)},{last3}"

stat(c1, "Total Invoices",  total,                        "in file")
stat(c2, "Overdue",         overdue_cnt,                  "need action",              "warn")
stat(c3, "Outstanding",     indian_format(outstanding),   f"across {overdue_cnt} invoices", "info")
stat(c4, "Critical (>30d)", escalated,                    "Stage 5 \u2014 legal flag",  "danger")

# ── Escalation Pipeline ───────────────────────────────────────────────────────
st.markdown("<div class='section-label'>Escalation Pipeline</div>", unsafe_allow_html=True)

def stage_count(min_d, max_d=None):
    if max_d:
        return len(df[(df["overdue_days"] >= min_d) & (df["overdue_days"] <= max_d)])
    return len(df[df["overdue_days"] > min_d])

s1 = stage_count(1, 7)
s2 = stage_count(8, 14)
s3 = stage_count(15, 21)
s4 = stage_count(22, 30)
s5 = stage_count(30)

p1, p2, p3, p4, p5 = st.columns(5)
for col, count, label, bg, color in [
    (p1, s1, "Stage 1 · Friendly",  "#eff6ff", "#2563eb"),
    (p2, s2, "Stage 2 · Firm",      "#f0fdf4", "#15803d"),
    (p3, s3, "Stage 3 · Serious",   "#fffbeb", "#b45309"),
    (p4, s4, "Stage 4 · Urgent",    "#fff1f2", "#be123c"),
    (p5, s5, "Stage 5 · Legal",     "#f9fafb", "#374151"),
]:
    with col:
        st.markdown(
            f"<div class='pipeline-box' style='background:{bg};border-color:{color}30'>"
            f"<div class='p-count' style='color:{color}'>{count}</div>"
            f"<div class='p-label'>{label}</div></div>",
            unsafe_allow_html=True,
        )

# ── Charts ────────────────────────────────────────────────────────────────────
st.markdown("<div class='section-label'>Analytics</div>", unsafe_allow_html=True)

chart_col1, chart_col2 = st.columns(2)

# Bar chart — Top 15 by days overdue
with chart_col1:
    top_overdue = (
        df[df["overdue_days"] > 0]
        .nlargest(15, "overdue_days")[["client_name", "overdue_days"]]
        .copy()
    )
    def get_stage(d):
        if d > 30:   return "Stage 5"
        elif d > 21: return "Stage 4"
        elif d > 14: return "Stage 3"
        elif d > 7:  return "Stage 2"
        else:        return "Stage 1"
    top_overdue["stage"] = top_overdue["overdue_days"].apply(get_stage)
    color_map = {
        "Stage 1": "#2563eb",
        "Stage 2": "#15803d",
        "Stage 3": "#b45309",
        "Stage 4": "#be123c",
        "Stage 5": "#6b7280",
    }
    fig_bar = px.bar(
        top_overdue,
        x="overdue_days",
        y="client_name",
        orientation="h",
        color="stage",
        color_discrete_map=color_map,
        labels={"overdue_days": "Days Overdue", "client_name": ""},
        title="Top Invoices by Days Overdue",
    )
    fig_bar.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter",
        font_color="#374151",
        title_font_size=13,
        title_font_color="#111827",
        showlegend=True,
        legend_title_text="",
        height=380,
        margin=dict(l=0, r=10, t=40, b=10),
        xaxis=dict(gridcolor="#f3f4f6", showline=False),
        yaxis=dict(gridcolor="#f3f4f6", showline=False),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# Pie chart — Stage distribution
with chart_col2:
    stage_data = {
        "Stage 1 · Friendly": s1,
        "Stage 2 · Firm":     s2,
        "Stage 3 · Serious":  s3,
        "Stage 4 · Urgent":   s4,
        "Stage 5 · Legal":    s5,
    }
    stage_data = {k: v for k, v in stage_data.items() if v > 0}
    fig_pie = go.Figure(data=[go.Pie(
        labels=list(stage_data.keys()),
        values=list(stage_data.values()),
        hole=0.52,
        marker_colors=["#2563eb", "#15803d", "#b45309", "#be123c", "#6b7280"],
        textfont_size=12,
    )])
    fig_pie.update_layout(
        title="Stage Distribution",
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Inter",
        font_color="#374151",
        title_font_size=13,
        title_font_color="#111827",
        height=380,
        margin=dict(l=0, r=0, t=40, b=10),
        legend=dict(orientation="v", font_size=11),
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# ── Invoice Table ─────────────────────────────────────────────────────────────
st.markdown("<div class='section-label'>Invoice Overview</div>", unsafe_allow_html=True)

def status_label(d):
    if d <= 0:  return "Not due"
    if d > 30:  return f"Escalated ({d}d)"
    return f"{d}d overdue"

df["status"] = df["overdue_days"].apply(status_label)
st.dataframe(
    df[["invoice_no", "client_name", "amount_due", "due_date", "overdue_days", "status"]],
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

st.markdown("<hr>", unsafe_allow_html=True)

# ── Run Agent ─────────────────────────────────────────────────────────────────
col_btn, col_note = st.columns([1, 4])
with col_btn:
    run_clicked = st.button("Run Agent", use_container_width=True)
with col_note:
    st.markdown(
        "<p style='font-size:0.8rem;color:#9ca3af;margin-top:10px'>"
        "Generates follow-up emails for all overdue invoices. No real emails are sent.</p>",
        unsafe_allow_html=True,
    )

# ── Results ───────────────────────────────────────────────────────────────────
if run_clicked:
    with st.spinner("Running agent…"):
        try:
            summary = run_agent(csv_path)
        except Exception as e:
            st.error(f"Agent error: {e}")
            st.stop()

    st.markdown("<div class='section-label'>Run Summary</div>", unsafe_allow_html=True)
    r1, r2, r3, r4 = st.columns(4)
    stat(r1, "Total Invoices",    summary["total"],            "in file")
    stat(r2, "Overdue",           summary["overdue"],          "need action",      "warn")
    stat(r3, "Emails Generated",  summary["emails_generated"], "dry-run complete", "ok")
    stat(r4, "Escalated",         summary["escalated"],        ">30 days",         "danger")

    stage_pill = {1:"pill-blue", 2:"pill-green", 3:"pill-yellow", 4:"pill-red"}

    emailed   = [r for r in summary["results"] if r["send_status"] not in ("skipped","escalated")]
    escalated_list = [r for r in summary["results"] if r["send_status"] == "escalated"]
    skipped   = [r for r in summary["results"] if r["send_status"] == "skipped"]

    if emailed:
        st.markdown("<div class='section-label'>Generated Emails</div>", unsafe_allow_html=True)
        for r in emailed:
            pill_cls = stage_pill.get(r["stage"], "pill-gray")
            with st.expander(f"{r['invoice_no']} — {r['client_name']}"):
                mc1, mc2, mc3 = st.columns([2, 1, 1])
                mc1.markdown(f"<div style='font-size:0.8rem;color:#6b7280'>{r['client_name']}</div>", unsafe_allow_html=True)
                mc2.markdown(f"<div style='font-size:0.8rem;color:#6b7280'>${r.get('amount_due',0):,.2f}</div>", unsafe_allow_html=True)
                mc3.markdown(f"<span class='pill {pill_cls}'>Stage {r['stage']} · {r['overdue_days']}d overdue</span>", unsafe_allow_html=True)
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:0.72rem;color:#9ca3af;margin-bottom:4px'>Subject</div><div class='email-subject'>{r['subject']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:0.72rem;color:#9ca3af;margin-bottom:4px'>Email Body</div><div class='email-body-box'>{r['body']}</div>", unsafe_allow_html=True)
                st.markdown("<div style='margin-top:10px'><span class='pill pill-sent'>Sent (dry-run)</span></div>", unsafe_allow_html=True)

    if escalated_list:
        st.markdown("<div class='section-label'>Escalated — Legal Review Required</div>", unsafe_allow_html=True)
        for r in escalated_list:
            st.markdown(
                f"<div class='esc-card'>"
                f"<div class='esc-card-title'>{r['invoice_no']} — {r['client_name']}</div>"
                f"<div class='esc-card-meta'>{r['overdue_days']} days overdue · No email sent · Flagged for manual review</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    if skipped:
        st.markdown("<div class='section-label'>Not Overdue — Skipped</div>", unsafe_allow_html=True)
        rows = "".join(
            f"<div style='font-size:0.8rem;color:#6b7280;padding:4px 0;border-bottom:1px solid #f3f4f6'>"
            f"{r['invoice_no']} &nbsp;·&nbsp; {r['client_name']}</div>"
            for r in skipped
        )
        st.markdown(f"<div style='border:1px solid #e5e7eb;border-radius:8px;padding:8px 14px'>{rows}</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-label'>Audit Log</div>", unsafe_allow_html=True)
    log_path = os.path.join("logs", "emails_log.json")
    if os.path.exists(log_path):
        log_data = load_json_file(log_path)
        if log_data:
            log_df = pd.DataFrame(log_data)[
                ["timestamp","invoice_no","client_name","overdue_days",
                 "escalation_stage","tone_used","email_subject","send_status"]
            ]
            st.dataframe(log_df, use_container_width=True, hide_index=True)

    st.markdown(
        "<p style='font-size:0.75rem;color:#9ca3af;margin-top:8px'>"
        "Logs → <code>logs/emails_log.json</code> · <code>logs/escalated_accounts.json</code></p>",
        unsafe_allow_html=True,
    )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<p style='font-size:0.72rem;color:#d1d5db;text-align:center'>"
    "Finance Follow-Up Agent · LangChain + GPT-4o-mini · Dry-run mode</p>",
    unsafe_allow_html=True,
)
