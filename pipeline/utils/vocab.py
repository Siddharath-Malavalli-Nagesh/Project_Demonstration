"""
Controlled vocabulary definitions and validators for the fraud detection pipeline.
All LLM outputs are validated against these enums before being persisted.
"""
from enum import Enum


class SuspicionClassification(str, Enum):
    CLEAN = "clean"
    SLOPPY = "sloppy"
    SYNTHETIC_SIGNUPS = "synthetic_signups"
    ACCOUNT_FARMING = "account_farming"
    INCENTIVE_ABUSE = "incentive_abuse"
    INCONCLUSIVE = "inconclusive"


class PayoutRecommendation(str, Enum):
    PAY_IN_FULL = "pay_in_full"
    PAY_PARTIAL = "pay_partial"
    HOLD_PENDING_REVIEW = "hold_pending_review"
    CLAWBACK = "clawback"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# String sets for fast membership checks
SUSPICION_CLASSIFICATIONS = {e.value for e in SuspicionClassification}
PAYOUT_RECOMMENDATIONS = {e.value for e in PayoutRecommendation}
RISK_LEVELS = {e.value for e in RiskLevel}
CONFIDENCE_LEVELS = {e.value for e in ConfidenceLevel}

_VOCAB_REGISTRY = {
    "SUSPICION_CLASSIFICATIONS": SUSPICION_CLASSIFICATIONS,
    "PAYOUT_RECOMMENDATIONS": PAYOUT_RECOMMENDATIONS,
    "RISK_LEVELS": RISK_LEVELS,
    "CONFIDENCE_LEVELS": CONFIDENCE_LEVELS,
}


def validate_vocab(value: str, vocab_name: str) -> str:
    """Raises ValueError if value is not in the named controlled vocabulary."""
    vocab = _VOCAB_REGISTRY.get(vocab_name)
    if vocab is None:
        raise KeyError(f"Unknown vocabulary: {vocab_name}")
    if value not in vocab:
        raise ValueError(
            f"'{value}' is not a valid {vocab_name} value. Allowed: {sorted(vocab)}"
        )
    return value
