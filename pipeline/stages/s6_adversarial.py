"""
Stage 6 — Adversarial self-review via Gemini.
Argues the affiliate's defense; applies any warranted downgrades in-memory.
"""
import json
from pathlib import Path

from utils.gemini import call_gemini, parse_json_response
from utils.vocab import validate_vocab, PAYOUT_RECOMMENDATIONS

FEATURES_FILE = Path(__file__).parent.parent / "affiliate_features.json"
CLASSIFICATIONS_FILE = Path(__file__).parent.parent / "classifications.json"
SCORES_FILE = Path(__file__).parent.parent / "quality_scores.json"
PAYOUTS_FILE = Path(__file__).parent.parent / "payouts.json"
OUTPUT_FILE = Path(__file__).parent.parent / "adversarial_review.json"

_DOWNGRADE_ALLOWED = {"pay_partial", "hold_pending_review"}


def build_prompt(affiliates: list[dict]) -> str:
    return f"""You are a defense attorney reviewing affiliate fraud determinations.
Your role is to identify the strongest benign explanations for each suspicious signal.

## Instructions
For each affiliate below:
- Assume a defense attorney role with non-accusatory framing
- Identify the strongest benign explanation for each suspicious signal
- Explicitly consider: legitimate promo bursts, country-specific email norms, device sharing in households/offices, cohort immaturity, incomplete 30-day observation window
- Assess the overall credibility of the defense
- Recommend whether to maintain the current payout recommendation or downgrade it

If recommending a downgrade, set recommended_action to "downgrade" and specify downgrade_to.
If maintaining, set recommended_action to "maintain" and set downgrade_to to null.

## Affiliate Data
{json.dumps(affiliates, indent=2)}

Respond only with valid JSON. Do not include markdown code fences, preamble, or explanation outside the JSON.

Return a JSON array:
[
  {{
    "affiliate_id": "aff_001",
    "defense_arguments": [
      {{
        "signal": "<feature name and value>",
        "benign_explanation": "<explanation>",
        "credibility": "<low | medium | high>"
      }}
    ],
    "overall_defense_strength": "<low | medium | high>",
    "recommended_action": "<maintain | downgrade>",
    "downgrade_to": "<pay_partial | hold_pending_review | null>",
    "downgrade_rationale": "<string or null>"
  }}
]
"""


def run(
    features_file: Path = FEATURES_FILE,
    classifications_file: Path = CLASSIFICATIONS_FILE,
    scores_file: Path = SCORES_FILE,
    payouts_file: Path = PAYOUTS_FILE,
    output_file: Path = OUTPUT_FILE,
) -> tuple[list[dict], list[dict]]:
    with open(features_file) as f:
        features = json.load(f)
    with open(classifications_file) as f:
        classifications = json.load(f)
    with open(scores_file) as f:
        scores = json.load(f)
    with open(payouts_file) as f:
        payouts = json.load(f)

    feat_map = {x["affiliate_id"]: x for x in features}
    cls_map = {x["affiliate_id"]: x for x in classifications}
    score_map = {x["affiliate_id"]: x for x in scores}

    non_full_payouts = [p for p in payouts if p["recommendation"] != "pay_in_full"]

    if not non_full_payouts:
        print("[s6_adversarial] No non-pay_in_full affiliates; skipping.")
        with open(output_file, "w") as f:
            json.dump([], f)
        return [], payouts

    affiliates_data = [
        {
            "affiliate_id": p["affiliate_id"],
            "current_recommendation": p["recommendation"],
            "features": feat_map[p["affiliate_id"]],
            "classification": cls_map[p["affiliate_id"]],
            "quality_score": score_map[p["affiliate_id"]],
            "payout": p,
        }
        for p in non_full_payouts
    ]

    prompt = build_prompt(affiliates_data)
    raw = call_gemini(
        prompt=prompt,
        stage="OPTIONAL_REVIEWS_GENERATED",
        affiliate_id=None,
        input_artifacts=[
            "affiliate_features.json",
            "classifications.json",
            "quality_scores.json",
            "payouts.json",
        ],
        output_artifact="adversarial_review.json",
    )

    reviews = parse_json_response(raw, "OPTIONAL_REVIEWS_GENERATED")

    if not isinstance(reviews, list):
        raise ValueError("Expected a JSON array from adversarial review stage")

    # Apply downgrades to in-memory payouts
    payout_map = {p["affiliate_id"]: p for p in payouts}
    for review in reviews:
        aff_id = review["affiliate_id"]
        if review.get("recommended_action") == "downgrade":
            downgrade_to = review.get("downgrade_to")
            if downgrade_to and downgrade_to in _DOWNGRADE_ALLOWED:
                validate_vocab(downgrade_to, "PAYOUT_RECOMMENDATIONS")
                old = payout_map[aff_id]["recommendation"]
                payout_map[aff_id]["recommendation"] = downgrade_to
                payout_map[aff_id]["adversarial_downgrade_from"] = old
                payout_map[aff_id]["adversarial_downgrade_rationale"] = review.get("downgrade_rationale")
                print(f"[s6_adversarial] Downgraded {aff_id}: {old} → {downgrade_to}")

    updated_payouts = list(payout_map.values())

    with open(payouts_file, "w") as f:
        json.dump(updated_payouts, f, indent=2)

    with open(output_file, "w") as f:
        json.dump(reviews, f, indent=2)

    print(f"[s6_adversarial] Adversarial review complete → {output_file}")
    return reviews, updated_payouts
