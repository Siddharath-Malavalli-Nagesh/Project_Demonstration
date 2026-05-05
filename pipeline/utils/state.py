"""
Pipeline state machine. Enforces ordered stage execution and timestamps transitions.
"""
from datetime import datetime, timezone
from enum import IntEnum


class Stage(IntEnum):
    INIT = 0
    INPUTS_LOADED = 1
    DATASET_EXTENDED_OR_VALIDATED = 2
    FEATURES_COMPUTED = 3
    PATTERNS_CLASSIFIED = 4
    QUALITY_SCORES_COMPUTED = 5
    PAYOUTS_RECOMMENDED = 6
    JUSTIFICATIONS_GENERATED = 7
    OPTIONAL_REVIEWS_GENERATED = 8
    VALIDATION_COMPLETE = 9
    RESULTS_FINALISED = 10


class PipelineState:
    def __init__(self) -> None:
        self._current = Stage.INIT
        self._log: list[tuple[Stage, str]] = []
        self._record(Stage.INIT)

    @property
    def current(self) -> Stage:
        return self._current

    def advance(self, target: Stage) -> None:
        expected = Stage(self._current + 1)
        if target != expected:
            raise RuntimeError(
                f"Stage ordering violation: current={self._current.name}, "
                f"attempted={target.name}, expected={expected.name}"
            )
        self._current = target
        self._record(target)

    def _record(self, stage: Stage) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        self._log.append((stage, ts))
        print(f"[{ts}] STAGE → {stage.name}")

    def transition_log(self) -> list[dict]:
        return [{"stage": s.name, "timestamp": ts} for s, ts in self._log]
