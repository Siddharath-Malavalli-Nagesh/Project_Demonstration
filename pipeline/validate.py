"""
Validation script for the affiliate fraud detection pipeline.
Exits 0 on full pass, 1 if any required check fails.
Warnings do not affect the exit code.
"""
import json
import sys
from pathlib import Path

BASE = Path(__file__).parent

sys.path.insert(0, str(BASE))

from utils.vocab import SUSPICION_CLASSIFICATIONS, PAYOUT_RECOMMENDATIONS

REQUIRED_JUSTIFICATION_SECTIONS = [
    "## Observed Signals",
    "## Statistical Evidence",
    "## Policy Clauses Referenced",
    "## Example Signup IDs Under Review",
    "## Reason for Recommendation",
    "## What Would Change This Decision",
]

_failures = 0
_warnings = 0


def _pass(label: str) -> None:
    print(f"  PASS  {label}")


def _fail(label: str, detail: str = "") -> None:
    global _failures
    _failures += 1
    msg = f"  FAIL  {label}"
    if detail:
        msg += f"\n        {detail}"
    print(msg)


def _warn(label: str, detail: str = "") -> None:
    global _warnings
    _warnings += 1
    msg = f"  WARN  {label}"
    if detail:
        msg += f"\n        {detail}"
    print(msg)


def _load_json(path: Path) -> tuple[bool, object]:
    if not path.exists():
        return False, None
    try:
        with open(path) as f:
            return True, json.load(f)
    except json.JSONDecodeError as e:
        return False, str(e)


def main() -> None:
    print("=" * 60)
    print("Pipeline Output Validation")
    print("=" * 60)

    # --- Input files ---
    print("\n[Input Files]")

    ok, signups = _load_json(BASE / "data" / "signups.json")
    if ok and isinstance(signups, list):
        _pass("signups.json exists and is valid JSON")
    else:
        _fail("signups.json exists and is valid JSON", str(signups or "file not found"))

    ok, trades = _load_json(BASE / "data" / "deposit_and_trade_summary.json")
    if ok and isinstance(trades, list):
        _pass("deposit_and_trade_summary.json exists and is valid JSON")
    else:
        _fail("deposit_and_trade_summary.json exists and is valid JSON", str(trades or "file not found"))

    ok, policy = _load_json(BASE / "data" / "payout_policy.json")
    if ok and isinstance(policy, dict):
        _pass("payout_policy.json exists and is valid JSON")
    else:
        _fail("payout_policy.json exists and is valid JSON", str(policy or "file not found"))

    # --- Features ---
    print("\n[Features]")
    ok, features = _load_json(BASE / "affiliate_features.json")
    if not ok or not isinstance(features, list):
        _fail("affiliate_features.json exists", str(features or "file not found"))
        features = []
    else:
        _pass("affiliate_features.json exists")

    # Collect affiliate IDs from features
    feature_aff_ids = {f["affiliate_id"] for f in features} if features else set()
    expected_affiliates = {"aff_001", "aff_002", "aff_003", "aff_004", "aff_005", "aff_006"}

    if features:
        if feature_aff_ids >= expected_affiliates:
            _pass("affiliate_features.json contains one record per affiliate")
        else:
            missing = expected_affiliates - feature_aff_ids
            _fail("affiliate_features.json contains one record per affiliate", f"Missing: {missing}")

        missing_fields = [
            f["affiliate_id"]
            for f in features
            if "total_signups" not in f or "total_signups_with_trade_data" not in f
        ]
        if not missing_fields:
            _pass("Every feature record includes total_signups and total_signups_with_trade_data")
        else:
            _fail("Every feature record includes total_signups and total_signups_with_trade_data",
                  f"Missing in: {missing_fields}")

    # --- Classifications ---
    print("\n[Classifications]")
    ok, classifications = _load_json(BASE / "classifications.json")
    if not ok or not isinstance(classifications, list):
        _fail("classifications.json exists", str(classifications or "file not found"))
        classifications = []
    else:
        _pass("classifications.json exists")

    if classifications:
        bad_cls = [
            c["affiliate_id"]
            for c in classifications
            if c.get("classification") not in SUSPICION_CLASSIFICATIONS
        ]
        if not bad_cls:
            _pass("Every classification uses only allowed SUSPICION_CLASSIFICATIONS values")
        else:
            _fail("Every classification uses only allowed SUSPICION_CLASSIFICATIONS values",
                  f"Bad affiliates: {bad_cls}")

        missing_tf = [
            c["affiliate_id"]
            for c in classifications
            if not c.get("triggering_features")
            or not any(isinstance(tf.get("value"), (int, float)) for tf in c["triggering_features"])
        ]
        if not missing_tf:
            _pass("Every classification includes at least one triggering_feature with a numeric value")
        else:
            _fail("Every classification includes at least one triggering_feature with a numeric value",
                  f"Affected: {missing_tf}")

        missing_ids = [
            c["affiliate_id"]
            for c in classifications
            if not c.get("example_signup_ids")
        ]
        if not missing_ids:
            _pass("Every classification includes at least one example_signup_id")
        else:
            _fail("Every classification includes at least one example_signup_id",
                  f"Affected: {missing_ids}")

    # --- Quality Scores ---
    print("\n[Quality Scores]")
    ok, scores = _load_json(BASE / "quality_scores.json")
    if not ok or not isinstance(scores, list):
        _fail("quality_scores.json exists", str(scores or "file not found"))
        scores = []
    else:
        _pass("quality_scores.json exists")

    model_doc = BASE / "quality_score_model.md"
    if model_doc.exists() and model_doc.stat().st_size > 0:
        _pass("quality_score_model.md exists and is non-empty")
    else:
        _fail("quality_score_model.md exists and is non-empty")

    if scores:
        bad_range = [
            s["affiliate_id"]
            for s in scores
            if not (0 <= s.get("quality_score", -1) <= 100)
        ]
        if not bad_range:
            _pass("Every quality score is between 0 and 100")
        else:
            _fail("Every quality score is between 0 and 100", f"Out of range: {bad_range}")

        missing_components = [
            s["affiliate_id"]
            for s in scores
            if not s.get("component_scores")
        ]
        if not missing_components:
            _pass("Every quality score includes component_scores")
        else:
            _fail("Every quality score includes component_scores", f"Missing in: {missing_components}")

    # --- Payouts ---
    print("\n[Payouts]")
    ok, payouts = _load_json(BASE / "payouts.json")
    if not ok or not isinstance(payouts, list):
        _fail("payouts.json exists", str(payouts or "file not found"))
        payouts = []
    else:
        _pass("payouts.json exists")

    if payouts:
        bad_rec = [
            p["affiliate_id"]
            for p in payouts
            if p.get("recommendation") not in PAYOUT_RECOMMENDATIONS
        ]
        if not bad_rec:
            _pass("Every recommendation uses only allowed PAYOUT_RECOMMENDATIONS values")
        else:
            _fail("Every recommendation uses only allowed PAYOUT_RECOMMENDATIONS values",
                  f"Bad affiliates: {bad_rec}")

        missing_policy_refs = [
            p["affiliate_id"]
            for p in payouts
            if not p.get("policy_references")
        ]
        if not missing_policy_refs:
            _pass("Every recommendation includes at least one policy_reference")
        else:
            _fail("Every recommendation includes at least one policy_reference",
                  f"Missing in: {missing_policy_refs}")

        bad_partial = [
            p["affiliate_id"]
            for p in payouts
            if p.get("recommendation") == "pay_partial"
            and p.get("pay_partial_percent") is None
        ]
        if not bad_partial:
            _pass("Every pay_partial recommendation has a non-null pay_partial_percent")
        else:
            _fail("Every pay_partial recommendation has a non-null pay_partial_percent",
                  f"Missing percent in: {bad_partial}")

    # --- Justifications ---
    print("\n[Justifications]")
    non_full_ids = [
        p["affiliate_id"]
        for p in payouts
        if p.get("recommendation") != "pay_in_full"
    ] if payouts else []

    for aff_id in non_full_ids:
        jpath = BASE / "justifications" / f"{aff_id}.md"
        if not jpath.exists():
            _fail(f"justifications/{aff_id}.md exists")
            continue
        _pass(f"justifications/{aff_id}.md exists")

        content = jpath.read_text()
        missing_sections = [
            sec for sec in REQUIRED_JUSTIFICATION_SECTIONS if sec not in content
        ]
        if not missing_sections:
            _pass(f"justifications/{aff_id}.md contains all 6 required sections")
        else:
            _fail(f"justifications/{aff_id}.md contains all 6 required sections",
                  f"Missing: {missing_sections}")

    # --- LLM Call Log ---
    print("\n[LLM Call Log]")
    llm_log_path = BASE / "llm_calls.jsonl"
    if not llm_log_path.exists():
        _fail("llm_calls.jsonl exists")
        llm_records = []
    else:
        _pass("llm_calls.jsonl exists")
        llm_records = []
        with open(llm_log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        llm_records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    if llm_records:
        stages_logged = {r.get("stage") for r in llm_records}

        if "PATTERNS_CLASSIFIED" in stages_logged:
            _pass("llm_calls.jsonl contains a record with stage PATTERNS_CLASSIFIED")
        else:
            _fail("llm_calls.jsonl contains a record with stage PATTERNS_CLASSIFIED")

        if "PAYOUTS_RECOMMENDED" in stages_logged:
            _pass("llm_calls.jsonl contains a record with stage PAYOUTS_RECOMMENDED")
        else:
            _fail("llm_calls.jsonl contains a record with stage PAYOUTS_RECOMMENDED")

        just_records = [r for r in llm_records if r.get("stage") == "JUSTIFICATIONS_GENERATED"]
        just_aff_ids = {r.get("affiliate_id") for r in just_records}
        missing_just_log = set(non_full_ids) - just_aff_ids
        if not missing_just_log:
            _pass("llm_calls.jsonl contains one JUSTIFICATIONS_GENERATED record per non-pay_in_full affiliate")
        else:
            _fail("llm_calls.jsonl contains one JUSTIFICATIONS_GENERATED record per non-pay_in_full affiliate",
                  f"Missing log entries for: {missing_just_log}")

    # --- Classification sanity checks ---
    print("\n[Classification Sanity]")
    cls_map = {c["affiliate_id"]: c["classification"] for c in classifications} if classifications else {}

    if "aff_001" in cls_map:
        if cls_map["aff_001"] != "clean":
            _pass("aff_001 classification is NOT 'clean'")
        else:
            _fail("aff_001 classification is NOT 'clean'", f"Got: {cls_map['aff_001']}")
    else:
        _warn("aff_001 not found in classifications")

    if "aff_003" in cls_map:
        if cls_map["aff_003"] != "clean":
            _pass("aff_003 classification is NOT 'clean'")
        else:
            _fail("aff_003 classification is NOT 'clean'", f"Got: {cls_map['aff_003']}")
    else:
        _warn("aff_003 not found in classifications")

    # --- Optional outputs (warn only) ---
    print("\n[Optional Outputs]")
    if (BASE / "adversarial_review.json").exists():
        _pass("adversarial_review.json exists")
    else:
        _warn("adversarial_review.json missing (optional)")

    if (BASE / "ltv_forecast.json").exists():
        _pass("ltv_forecast.json exists")
    else:
        _warn("ltv_forecast.json missing (optional)")

    # --- Summary ---
    print("\n" + "=" * 60)
    print(f"Result: {_failures} failure(s), {_warnings} warning(s)")
    print("=" * 60)

    sys.exit(0 if _failures == 0 else 1)


if __name__ == "__main__":
    main()
