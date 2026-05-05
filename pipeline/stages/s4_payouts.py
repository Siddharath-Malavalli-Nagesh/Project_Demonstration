"""
Stage 4 — Payout recommendations via a single Gemini call.
Validates recommendations and risk levels against controlled vocabularies.
"""
import json
from pathlib import Path

from utils.gemini import call_gemini, parse_json_response
from utils.vocab import validate_vocab

DATA_DIR = Path(__file__).parent.parent / "data"
FEATURES_FILE = Path(__file__).parent.parent / "affiliate_features.json"
CLASSIFICATIONS_FILE = Path(__file__).parent.parent / "classifications.json"
SCORES_FILE = Path(__file__).parent.parent / "quality_scores.json"
OUTPUT_FILE = Path(__file__).parent.parent / "payouts.json"


def _sample_signup_ids(signups: list[dict], affiliate_id: str, n: int = 5) -> list[str]:
    aff = sorted(
        [s["signup_id"] for s in signups if s["affiliate_id"] == affiliate_id]
    )
    return aff[:n]


def build_prompt(
    features: list[dict],
    classifications: list[dict],
    scores: list[dict],
    policy: dict,
    signups: list[dict],
) -> str:
    cls_map = {c["affiliate_id"]: c for c in classifications}
    score_map = {s["affiliate_id"]: s for s in scores}

    affiliate_blocks = []
    for feat in features:
        aff_id = feat["affiliate_id"]
        affiliate_blocks.append({
            "affiliate_id": aff_id,
            "features": feat,
            "classification": cls_map.get(aff_id),
            "quality_score": score_map.get(aff_id),
            "representative_signup_ids": _sample_signup_ids(signups, aff_id),
        })

    return f"""You are a compliance officer determining affiliate payout recommendations.

## Payout Policy
{json.dumps(policy, indent=2)}

## Allowed Recommendation Values
- pay_in_full      — Full payout, no concerns
- pay_partial      — Partial payout with a specified percentage (1–100)
- hold_pending_review — Withhold payout pending manual investigation
- clawback         — Recover previously paid commissions

## Allowed Risk Level Values
- low | medium | high | critical

## Affiliate Data
{json.dumps(affiliate_blocks, indent=2)}

## Instructions
For each affiliate, recommend a payout action grounded in the policy and evidence.
When recommendation is pay_partial, you MUST include a non-null pay_partial_percent (integer 1-100).
policy_references must be non-empty — list the policy rule keys that drove your decision.

Respond only with valid JSON. Do not include markdown code fences, preamble, or explanation outside the JSON.

Return a JSON array with one object per affiliate:
[
  {{
    "affiliate_id": "aff_001",
    "recommendation": "<pay_in_full | pay_partial | hold_pending_review | clawback>",
    "pay_partial_percent": <integer or null>,
    "policy_references": ["<policy_key>", ...],
    "evidence_summary": "<concise summary>",
    "example_signup_ids": ["<id>", ...],
    "risk_level": "<low | medium | high | critical>"
  }}
]
"""


def run(
    features_file: Path = FEATURES_FILE,
    classifications_file: Path = CLASSIFICATIONS_FILE,
    scores_file: Path = SCORES_FILE,
    data_dir: Path = DATA_DIR,
    output_file: Path = OUTPUT_FILE,
) -> list[dict]:
    with open(features_file) as f:
        features = json.load(f)
    with open(classifications_file) as f:
        classifications = json.load(f)
    with open(scores_file) as f:
        scores = json.load(f)
    with open(data_dir / "payout_policy.json") as f:
        policy = json.load(f)
    with open(data_dir / "signups.json") as f:
        signups = json.load(f)

    prompt = build_prompt(features, classifications, scores, policy, signups)

    raw = call_gemini(
        prompt=prompt,
        stage="PAYOUTS_RECOMMENDED",
        affiliate_id=None,
        input_artifacts=[
            "affiliate_features.json",
            "classifications.json",
            "quality_scores.json",
            "payout_policy.json",
        ],
        output_artifact="payouts.json",
    )

    payouts = parse_json_response(raw, "PAYOUTS_RECOMMENDED")

    if not isinstance(payouts, list):
        raise ValueError("Expected a JSON array from payout stage")

    for record in payouts:
        validate_vocab(record["recommendation"], "PAYOUT_RECOMMENDATIONS")
        validate_vocab(record["risk_level"], "RISK_LEVELS")
        if record["recommendation"] == "pay_partial" and record.get("pay_partial_percent") is None:
            raise ValueError(
                f"pay_partial_percent must be non-null for pay_partial: {record['affiliate_id']}"
            )
        if not record.get("policy_references"):
            raise ValueError(f"policy_references must be non-empty for {record['affiliate_id']}")

    with open(output_file, "w") as f:
        json.dump(payouts, f, indent=2)

    print(f"[s4_payouts] Recommended payouts for {len(payouts)} affiliates → {output_file}")
    return payouts
