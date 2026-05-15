"""
utils/helpers.py
────────────────
Shared helper functions for the Finance Follow-Up Agent.
"""

import json
import os
from datetime import date


def load_json_file(filepath: str) -> list:
    """Load a JSON file and return its contents as a list.
    Returns an empty list if the file doesn't exist or is empty/corrupt."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError):
        return []


def save_json_file(filepath: str, data: list) -> None:
    """Persist a list to a JSON file, creating parent directories if needed."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def calculate_overdue_days(due_date_str: str) -> int:
    """Return the number of days an invoice is overdue from today.
    Returns 0 (not overdue) if the due date is today or in the future.
    Accepts ISO date strings: 'YYYY-MM-DD'.
    """
    try:
        due_date = date.fromisoformat(str(due_date_str).strip())
        delta = (date.today() - due_date).days
        return max(0, delta)
    except ValueError:
        return 0


def sanitize_text(text: str) -> str:
    """Basic input sanitization to reduce prompt injection surface.
    Strips leading/trailing whitespace and removes common injection patterns.
    """
    if not isinstance(text, str):
        text = str(text)
    # Remove characters that could break JSON or prompt structure
    dangerous = ["\n\n---", "IGNORE PREVIOUS", "</s>", "<<SYS>>", "[INST]"]
    for pattern in dangerous:
        text = text.replace(pattern, "")
    return text.strip()


def format_currency(amount) -> str:
    """Format a numeric amount as a USD currency string."""
    try:
        return f"${float(amount):,.2f}"
    except (ValueError, TypeError):
        return str(amount)
