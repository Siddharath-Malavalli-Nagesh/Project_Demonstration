"""
Stage 3 — Deterministic quality scoring. No Gemini calls.
Applies the documented scoring formula (see quality_score_model.md).
"""
import json
from pathlib import Path

from utils.vocab import validate_vocab, RiskLevel

FEATURES_FILE = Path(__file__).parent.parent / "affiliate_features.json"
CLASSIFICATIONS_FILE = Path(__file__).parent.parent / "classifications.json"
OUTPUT_FILE = Path(__file__).parent.parent / "quality_scores.json"
MODEL_DOC = Path(__file__).parent.parent / "quality_score_model.md"

FORMULA_VERSION = "v1.0"

MODEL_DOC_CONTENT = """\
# Quality Score Model — v1.0

## Overview
Scores are computed deterministically from affiliate feature vectors and classification labels.
Range: 0–100. Higher scores indicate higher traffic quality.

## Base Score
`base_score = 100`

## Penalties

### Classification Penalty
| Classification     | Penalty |
|--------------------|---------|
| synthetic_signups  | -40     |
| account_farming    | -35     |
| incentive_abuse    | -30     |
| sloppy             | -15     |
| inconclusive       | -5      |
| clean              | 0       |

### Device Fingerprint Reuse Penalty
- `device_fingerprint_reuse_rate > 0.5` → -15
- `device_fingerprint_reuse_rate > 0.2` → -7

### Signup Velocity Penalty
- `peak_signups_per_minute > 10` → -15
- `peak_signups_per_minute > 3` → -7

### IP /24 Concentration Penalty
- `ip_24_concentration > 0.7` → -10
- `ip_24_concentration > 0.4` → -5

### Disposable Email Penalty
- `disposable_email_rate > 0.5` → -10
- `disposable_email_rate > 0.2` → -5

### Dormant Account Penalty
- `dormant_account_rate > 0.7` → -10
- `dormant_account_rate > 0.4` → -5

## Bonuses

### Active Days Bonus
- `avg_first_30d_active_days > 10` → +10
- `avg_first_30d_active_days > 5` → +5

### Trade Count Bonus
- `avg_trades_count > 30` → +10
- `avg_trades_count > 10` → +5

### Deposit Retention Bonus
- `deposit_retention_rate > 0.5` → +10
- `deposit_retention_rate > 0.3` → +5

### Deposit Size Bonus
- `avg_total_deposits_usd > 200` → +5

## Final Score
`final_score = clamp(base_score + sum(bonuses) + sum(penalties), 0, 100)`

## Risk Level Mapping
| Score Range | Risk Level |
|-------------|------------|
| 75–100      | low        |
| 50–74       | medium     |
| 25–49       | high       |
| 0–24        | critical   |
"""

CLASSIFICATION_PENALTY = {
    "synthetic_signups": -40,
    "account_farming": -35,
    "incentive_abuse": -30,
    "sloppy": -15,
    "inconclusive": -5,
    "clean": 0,
}


def _risk_level(score: int) -> str:
    if score >= 75:
        return RiskLevel.LOW.value
    elif score >= 50:
        return RiskLevel.MEDIUM.value
    elif score >= 25:
        return RiskLevel.HIGH.value
    else:
        return RiskLevel.CRITICAL.value


def score_affiliate(feat: dict, classification: str) -> dict:
    base = 100
    components: dict[str, int] = {}

    # Classification penalty
    cls_pen = CLASSIFICATION_PENALTY.get(classification, 0)
    components["classification_penalty"] = cls_pen

    # Device fingerprint reuse penalty
    dfr = feat["device_fingerprint_reuse_rate"]
    if dfr > 0.5:
        components["device_reuse_penalty"] = -15
    elif dfr > 0.2:
        components["device_reuse_penalty"] = -7
    else:
        components["device_reuse_penalty"] = 0

    # Velocity penalty
    ppm = feat["peak_signups_per_minute"]
    if ppm > 10:
        components["velocity_penalty"] = -15
    elif ppm > 3:
        components["velocity_penalty"] = -7
    else:
        components["velocity_penalty"] = 0

    # IP /24 concentration penalty
    ip24 = feat["ip_24_concentration"]
    if ip24 > 0.7:
        components["ip_concentration_penalty"] = -10
    elif ip24 > 0.4:
        components["ip_concentration_penalty"] = -5
    else:
        components["ip_concentration_penalty"] = 0

    # Disposable email penalty
    der = feat["disposable_email_rate"]
    if der > 0.5:
        components["disposable_email_penalty"] = -10
    elif der > 0.2:
        components["disposable_email_penalty"] = -5
    else:
        components["disposable_email_penalty"] = 0

    # Dormant account penalty
    dar = feat["dormant_account_rate"]
    if dar > 0.7:
        components["dormant_penalty"] = -10
    elif dar > 0.4:
        components["dormant_penalty"] = -5
    else:
        components["dormant_penalty"] = 0

    # Active days bonus
    ald = feat["avg_first_30d_active_days"]
    if ald > 10:
        components["active_days_bonus"] = 10
    elif ald > 5:
        components["active_days_bonus"] = 5
    else:
        components["active_days_bonus"] = 0

    # Trade count bonus
    atc = feat["avg_trades_count"]
    if atc > 30:
        components["trades_bonus"] = 10
    elif atc > 10:
        components["trades_bonus"] = 5
    else:
        components["trades_bonus"] = 0

    # Deposit retention bonus
    drr = feat["deposit_retention_rate"]
    if drr > 0.5:
        components["deposit_retention_bonus"] = 10
    elif drr > 0.3:
        components["deposit_retention_bonus"] = 5
    else:
        components["deposit_retention_bonus"] = 0

    # Deposit size bonus
    atd = feat["avg_total_deposits_usd"]
    components["deposit_size_bonus"] = 5 if atd > 200 else 0

    total_adjustment = sum(components.values())
    final_score = max(0, min(100, base + total_adjustment))
    risk = _risk_level(final_score)

    positive_factors = [k for k, v in components.items() if v > 0]
    negative_factors = [k for k, v in components.items() if v < 0]

    return {
        "affiliate_id": feat["affiliate_id"],
        "quality_score": final_score,
        "risk_level": risk,
        "formula_version": FORMULA_VERSION,
        "component_scores": components,
        "positive_factors": positive_factors,
        "negative_factors": negative_factors,
    }


def run(
    features_file: Path = FEATURES_FILE,
    classifications_file: Path = CLASSIFICATIONS_FILE,
    output_file: Path = OUTPUT_FILE,
    model_doc: Path = MODEL_DOC,
) -> list[dict]:
    with open(features_file) as f:
        features = json.load(f)
    with open(classifications_file) as f:
        classifications = json.load(f)

    cls_map = {c["affiliate_id"]: c["classification"] for c in classifications}

    scores = []
    for feat in features:
        aff_id = feat["affiliate_id"]
        cls = cls_map.get(aff_id, "inconclusive")
        result = score_affiliate(feat, cls)
        validate_vocab(result["risk_level"], "RISK_LEVELS")
        scores.append(result)

    with open(output_file, "w") as f:
        json.dump(scores, f, indent=2)

    with open(model_doc, "w") as f:
        f.write(MODEL_DOC_CONTENT)

    print(f"[s3_scores] Scored {len(scores)} affiliates → {output_file}")
    return scores
