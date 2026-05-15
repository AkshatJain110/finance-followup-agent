"""
agents/email_generator.py
──────────────────────────
Generates personalized follow-up emails using OpenAI GPT-4o-mini
via LangChain. Returns a structured dict with subject + body.
"""

import json
import os

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_community.cache import SQLiteCache
import langchain
from dotenv import load_dotenv

from utils.helpers import sanitize_text

load_dotenv()

# ── LangChain SQLite cache — avoids duplicate API calls during dev ────────────
# Saves cost when same invoice is processed multiple times (e.g., testing)
langchain.llm_cache = SQLiteCache(database_path=".langchain_cache.db")

# ── LangSmith tracing — observability & bonus marks ───────────────────────────
# Set LANGCHAIN_API_KEY in .env to enable. Safe to skip if key not present.
if os.getenv("LANGCHAIN_API_KEY"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "finance-followup-agent"

# ── Load the prompt template from file ──────────────────────────────────────

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "email_prompt.txt")

with open(_PROMPT_PATH, "r", encoding="utf-8") as _f:
    _PROMPT_TEMPLATE_STR = _f.read()

_PROMPT = PromptTemplate(
    input_variables=[
        "client_name",
        "invoice_no",
        "amount_due",
        "due_date",
        "overdue_days",
        "payment_link",
        "stage",
        "tone",
    ],
    template=_PROMPT_TEMPLATE_STR,
)


def _get_llm() -> ChatOpenAI:
    """Instantiate the LangChain LLM (GPT-4o-mini)."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("sk-your"):
        raise EnvironmentError(
            "OPENAI_API_KEY is not set. Add it to your .env file."
        )
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.4,       # Slightly creative but predictable
        openai_api_key=api_key,
    )


def generate_email(
    client_name: str,
    invoice_no: str,
    amount_due: float,
    due_date: str,
    overdue_days: int,
    payment_link: str,
    stage: int,
    tone: str,
) -> dict:
    """
    Call GPT-4o-mini to generate a personalised follow-up email.

    Returns:
        {
            "subject": str,
            "body": str,
            "raw_response": str   # for debugging
        }

    Raises:
        ValueError  — if the LLM returns malformed JSON
        EnvironmentError — if API key is missing
    """
    # Sanitize all string inputs before sending to the LLM
    safe_inputs = {
        "client_name": sanitize_text(str(client_name)),
        "invoice_no": sanitize_text(str(invoice_no)),
        "amount_due": f"{float(amount_due):,.2f}",
        "due_date": sanitize_text(str(due_date)),
        "overdue_days": str(int(overdue_days)),
        "payment_link": sanitize_text(str(payment_link)),
        "stage": str(stage),
        "tone": sanitize_text(str(tone)),
    }

    llm = _get_llm()
    chain = _PROMPT | llm

    response = chain.invoke(safe_inputs)
    raw_text = response.content.strip()

    # ── Parse JSON response ──────────────────────────────────────────────────
    # Strip markdown code fences if the model wraps output in ```json ... ```
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM returned invalid JSON for {invoice_no}: {exc}\n"
            f"Raw response:\n{response.content}"
        ) from exc

    return {
        "subject": parsed.get("subject", "Follow-Up: Outstanding Invoice"),
        "body": parsed.get("body", ""),
        "raw_response": response.content,
    }
