"""
Gemini API wrapper with structured logging to llm_calls.jsonl.
Every call appends one JSON line atomically.
"""
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import google.generativeai as genai

LOG_FILE = Path(__file__).parent.parent / "llm_calls.jsonl"
MODEL = "gemini-2.5-pro"
MAX_RETRIES = 2


def _get_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise EnvironmentError(
            "GEMINI_API_KEY environment variable is not set. "
            "Export it before running the pipeline."
        )
    return key


def _log_call(
    stage: str,
    affiliate_id: Optional[str],
    prompt: str,
    input_artifacts: list[str],
    output_artifact: str,
) -> None:
    record = {
        "stage": stage,
        "affiliate_id": affiliate_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": "google",
        "model": MODEL,
        "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest(),
        "input_artifacts": input_artifacts,
        "output_artifact": output_artifact,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")


def call_gemini(
    prompt: str,
    stage: str,
    affiliate_id: Optional[str] = None,
    input_artifacts: Optional[list[str]] = None,
    output_artifact: str = "",
) -> str:
    """
    Call Gemini and log the call. Retries up to MAX_RETRIES times on failure.
    Returns raw text response.
    """
    genai.configure(api_key=_get_api_key())
    model = genai.GenerativeModel(MODEL)

    last_exc: Optional[Exception] = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = model.generate_content(prompt)
            text = response.text
            _log_call(
                stage=stage,
                affiliate_id=affiliate_id,
                prompt=prompt,
                input_artifacts=input_artifacts or [],
                output_artifact=output_artifact,
            )
            return text
        except Exception as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                wait = 2 ** attempt
                print(f"  [gemini] attempt {attempt + 1} failed ({exc}), retrying in {wait}s...")
                time.sleep(wait)

    raise RuntimeError(
        f"Gemini call failed after {MAX_RETRIES + 1} attempts in stage '{stage}': {last_exc}"
    ) from last_exc


def parse_json_response(raw: str, stage: str) -> object:
    """Strip markdown fences and parse JSON. Raises ValueError with stage context on failure."""
    text = raw.strip()
    # Remove ```json ... ``` or ``` ... ``` fences
    if text.startswith("```"):
        lines = text.splitlines()
        # drop first line (```json or ```) and last line (```)
        inner = lines[1:] if lines[-1].strip() == "```" else lines[1:]
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        text = "\n".join(inner).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"[{stage}] Failed to parse Gemini response as JSON: {exc}\n"
            f"Raw response (first 500 chars): {raw[:500]}"
        ) from exc
