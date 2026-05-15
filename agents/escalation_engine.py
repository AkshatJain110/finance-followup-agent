"""
agents/escalation_engine.py
────────────────────────────
Determines escalation stage and tone based on overdue days.
This is the core business-logic module — keep it pure (no I/O side effects).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class EscalationResult:
    """Holds the escalation decision for a single invoice."""
    stage: int
    tone: str
    should_email: bool          # False for Stage 5 (>30 days)
    flag_for_review: bool       # True for Stage 5


# ── Escalation table ────────────────────────────────────────────────────────

ESCALATION_STAGES = [
    {
        "stage": 1,
        "min_days": 1,
        "max_days": 7,
        "tone": "Warm & Friendly",
        "should_email": True,
        "flag_for_review": False,
    },
    {
        "stage": 2,
        "min_days": 8,
        "max_days": 14,
        "tone": "Polite but Firm",
        "should_email": True,
        "flag_for_review": False,
    },
    {
        "stage": 3,
        "min_days": 15,
        "max_days": 21,
        "tone": "Formal & Serious",
        "should_email": True,
        "flag_for_review": False,
    },
    {
        "stage": 4,
        "min_days": 22,
        "max_days": 30,
        "tone": "Stern & Urgent",
        "should_email": True,
        "flag_for_review": False,
    },
    {
        "stage": 5,
        "min_days": 31,
        "max_days": None,          # No upper bound
        "tone": "N/A — Legal Review",
        "should_email": False,
        "flag_for_review": True,
    },
]


def get_escalation(overdue_days: int) -> Optional[EscalationResult]:
    """Return the EscalationResult for the given number of overdue days.

    Returns None if the invoice is NOT overdue (overdue_days <= 0).
    """
    if overdue_days <= 0:
        return None  # Not overdue — skip processing

    for stage_def in ESCALATION_STAGES:
        min_d = stage_def["min_days"]
        max_d = stage_def["max_days"]

        if max_d is None:
            # Stage 5: anything above the lower bound
            if overdue_days >= min_d:
                return EscalationResult(
                    stage=stage_def["stage"],
                    tone=stage_def["tone"],
                    should_email=stage_def["should_email"],
                    flag_for_review=stage_def["flag_for_review"],
                )
        else:
            if min_d <= overdue_days <= max_d:
                return EscalationResult(
                    stage=stage_def["stage"],
                    tone=stage_def["tone"],
                    should_email=stage_def["should_email"],
                    flag_for_review=stage_def["flag_for_review"],
                )

    return None  # Shouldn't reach here with valid input
