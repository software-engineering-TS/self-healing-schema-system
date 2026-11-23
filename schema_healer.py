"""Orchestration, optional Ollama semantic matching and reconstruction."""
import json
import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd
import requests

from config import (AI_CONFIDENCE_THRESHOLD, OLLAMA_GENERATE, OLLAMA_MODEL,
                    OLLAMA_RETRY_DELAY, OLLAMA_RETRIES, OLLAMA_TAGS, OLLAMA_TIMEOUT)
from logger import logger
from matcher import MatchEngine, MatchReport, MatchResult
from utils import extract_json
from validator import SchemaValidator, ValidationReport


def check_ollama() -> bool:
    """Return whether the configured Ollama endpoint is reachable."""
    try:
        response = requests.get(OLLAMA_TAGS, timeout=min(5, OLLAMA_TIMEOUT))
        return response.status_code == 200
    except requests.RequestException as exc:
        logger.debug("Ollama health check failed: %s", exc)
        return False


def _call_ollama_with_retry(payload: dict) -> Optional[dict]:
    for attempt in range(1, max(1, OLLAMA_RETRIES) + 1):
        try:
            response = requests.post(OLLAMA_GENERATE, json=payload, timeout=OLLAMA_TIMEOUT)
            response.raise_for_status()
            body = response.json()
            return body if isinstance(body, dict) else None
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Ollama attempt %d/%d failed: %s", attempt, OLLAMA_RETRIES, exc)
            if attempt < OLLAMA_RETRIES:
                time.sleep(OLLAMA_RETRY_DELAY * attempt)
    return None


def _ai_match_columns(unmatched_expected: List[str], unmatched_actual: List[str]) -> List[MatchResult]:
    if not unmatched_expected or not unmatched_actual:
        return []
    prompt = f"""You are a data-engineering schema reconciliation assistant.
Map actual columns to semantically equivalent expected columns. Do not guess.
Every source and target may appear at most once. Omit uncertain mappings.
Return JSON only: {{\"mappings\":[{{\"actual\":\"...\",\"expected\":\"...\",\"confidence\":0.95}}]}}
Confidence must be a number from 0 to 1.
Expected columns: {json.dumps(unmatched_expected, ensure_ascii=False)}
Actual columns: {json.dumps(unmatched_actual, ensure_ascii=False)}
"""
    raw = _call_ollama_with_retry({"model": OLLAMA_MODEL, "prompt": prompt,
                                   "stream": False, "format": "json"})
    if not raw:
        raise RuntimeError("Ollama AI matching failed after retries")
    parsed = extract_json(raw.get("response", ""))
    if not isinstance(parsed, dict) or not isinstance(parsed.get("mappings"), list):
        logger.warning("Ollama returned an invalid mappings structure")
        return []

    expected_set, actual_set = set(unmatched_expected), set(unmatched_actual)
    results: List[MatchResult] = []
    for item in parsed["mappings"]:
        if not isinstance(item, dict):
            continue
        source, target = item.get("actual"), item.get("expected")
        confidence = item.get("confidence")
        if (not isinstance(source, str) or not isinstance(target, str)
                or source not in actual_set or target not in expected_set
                or isinstance(confidence, bool) or not isinstance(confidence, (int, float))
                or not math.isfinite(confidence) or not 0 <= confidence <= 1
                or confidence < AI_CONFIDENCE_THRESHOLD):
            continue
        results.append(MatchResult(source, target, "ai", float(confidence)))
        actual_set.remove(source)
        expected_set.remove(target)
    logger.info("AI returned %d validated mappings", len(results))
    return results


@dataclass
class HealingResult:
    healed_df: pd.DataFrame
    match_report: MatchReport
    validation_report: ValidationReport
    mapping: Dict[str, str]
    strategy_summary: Dict[str, int] = field(default_factory=dict)


def heal_schema(incoming_df: pd.DataFrame, expected_schema: List[str],
                ai_call=_ai_match_columns) -> HealingResult:
    """Run matching, validation and expected-schema reconstruction."""
    if not isinstance(incoming_df, pd.DataFrame):
        raise TypeError("incoming_df must be a pandas DataFrame")
    if incoming_df.empty and len(incoming_df.columns) == 0:
        raise ValueError("Incoming data must contain at least one column")
    actual_cols = list(incoming_df.columns)
    if len(actual_cols) != len(set(actual_cols)):
        raise ValueError("Incoming data contains duplicate column names; rename duplicates before healing")
    if not expected_schema:
        raise ValueError("Expected schema must contain at least one column")
    if len(expected_schema) != len(set(expected_schema)):
        raise ValueError("Expected schema contains duplicate column names")

    started = time.perf_counter()
    logger.info("=== Schema healing started | expected=%d actual=%d ===",
                len(expected_schema), len(actual_cols))
    effective_ai_call = ai_call
    ai_unavailable = False
    # Avoid waiting through generation retries when the default local service is offline.
    if ai_call is _ai_match_columns and not check_ollama():
        effective_ai_call = None
        ai_unavailable = True
        logger.info("Ollama is unavailable; skipping semantic matching")
    engine = MatchEngine(ai_call=effective_ai_call)
    match_report = engine.match(list(expected_schema), actual_cols)
    if ai_unavailable:
        match_report.ambiguity_warnings.append("Ollama unavailable; semantic matching was skipped")
    mapping = match_report.mapping
    validation = SchemaValidator(list(expected_schema), mapping, actual_cols).validate()
    validation.warnings.extend(match_report.ambiguity_warnings)
    healed_df = _reconstruct(incoming_df, expected_schema, mapping)
    summary = {
        "exact": len(match_report.exact_matches),
        "normalized": len(match_report.normalized_matches),
        "fuzzy": len(match_report.fuzzy_matches),
        "ai": len(match_report.ai_matches),
        "unmatched": len(match_report.unmatched_expected),
    }
    logger.info("=== Healing complete | %.2fs | %s ===", time.perf_counter() - started, summary)
    return HealingResult(healed_df, match_report, validation, mapping, summary)


def _reconstruct(df: pd.DataFrame, expected_schema: List[str], mapping: Dict[str, str]) -> pd.DataFrame:
    """Create exactly the expected columns in order; missing values remain pandas NA."""
    renamed = df.rename(columns=mapping, errors="raise")
    # Matching guarantees one-to-one targets; this check protects direct callers too.
    if len(set(mapping.values())) != len(mapping.values()):
        raise ValueError("Cannot reconstruct data: multiple source columns map to one target")
    output = renamed.reindex(columns=expected_schema)
    logger.info("Reconstructed DataFrame | shape=%s", output.shape)
    return output