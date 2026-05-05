"""
Pipeline orchestrator — runs all stages in order, enforcing state transitions.
"""
import sys
from pathlib import Path

# Allow imports from the pipeline root
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv()

from utils.state import PipelineState, Stage
from generate_seed_data import generate as generate_seed_data

import json

DATA_DIR = Path(__file__).parent / "data"
MIN_SIGNUPS = 50


def _needs_seed_data() -> bool:
    signups_path = DATA_DIR / "signups.json"
    if not signups_path.exists():
        return True
    try:
        with open(signups_path) as f:
            data = json.load(f)
        return len(data) < MIN_SIGNUPS
    except (json.JSONDecodeError, Exception):
        return True


def main() -> None:
    state = PipelineState()

    # Stage: INPUTS_LOADED — generate seed data if needed, then load inputs
    from stages import s1_features, s2_classify, s3_scores, s4_payouts
    from stages import s5_justifications, s6_adversarial, s7_ltv, s8_comms, s9_rules

    state.advance(Stage.INPUTS_LOADED)

    if _needs_seed_data():
        print("[main] Seed data missing or insufficient — generating...")
        generate_seed_data(DATA_DIR)
    else:
        print(f"[main] Seed data present — skipping generation.")

    state.advance(Stage.DATASET_EXTENDED_OR_VALIDATED)

    # Stage: FEATURES_COMPUTED
    features = s1_features.run()
    state.advance(Stage.FEATURES_COMPUTED)

    # Stage: PATTERNS_CLASSIFIED
    classifications = s2_classify.run()
    state.advance(Stage.PATTERNS_CLASSIFIED)

    # Stage: QUALITY_SCORES_COMPUTED
    scores = s3_scores.run()
    state.advance(Stage.QUALITY_SCORES_COMPUTED)

    # Stage: PAYOUTS_RECOMMENDED
    payouts = s4_payouts.run()
    state.advance(Stage.PAYOUTS_RECOMMENDED)

    # Stage: JUSTIFICATIONS_GENERATED
    s5_justifications.run()
    state.advance(Stage.JUSTIFICATIONS_GENERATED)

    # Stage: OPTIONAL_REVIEWS_GENERATED (adversarial review + LTV + comms + rules)
    s6_adversarial.run()
    s7_ltv.run()
    s8_comms.run()
    s9_rules.run()
    state.advance(Stage.OPTIONAL_REVIEWS_GENERATED)

    # Stage: VALIDATION_COMPLETE
    import subprocess
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "validate.py")],
        capture_output=False,
    )
    state.advance(Stage.VALIDATION_COMPLETE)

    # Stage: RESULTS_FINALISED
    state.advance(Stage.RESULTS_FINALISED)

    print("\n[main] Pipeline complete.")
    if result.returncode != 0:
        print("[main] WARNING: Validation reported failures — check output above.")
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
