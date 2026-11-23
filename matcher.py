"""Collision-safe four-stage column matching engine."""
from __future__ import annotations

import math
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from rapidfuzz import fuzz

from config import AI_CONFIDENCE_THRESHOLD, FUZZY_THRESHOLD
from logger import logger
from utils import normalize_column


@dataclass
class MatchResult:
    """A single source-to-target mapping and its provenance."""
    source_col: str
    target_col: str
    strategy: str
    confidence: float
    fuzzy_score: Optional[float] = None


@dataclass
class MatchReport:
    """Aggregated matching result."""
    matched: List[MatchResult] = field(default_factory=list)
    unmatched_expected: List[str] = field(default_factory=list)
    unmatched_actual: List[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    ambiguity_warnings: List[str] = field(default_factory=list)

    @property
    def mapping(self) -> Dict[str, str]:
        return {m.source_col: m.target_col for m in self.matched}

    @property
    def exact_matches(self) -> List[MatchResult]:
        return [m for m in self.matched if m.strategy == "exact"]

    @property
    def normalized_matches(self) -> List[MatchResult]:
        return [m for m in self.matched if m.strategy == "normalized"]

    @property
    def fuzzy_matches(self) -> List[MatchResult]:
        return [m for m in self.matched if m.strategy == "fuzzy"]

    @property
    def ai_matches(self) -> List[MatchResult]:
        return [m for m in self.matched if m.strategy == "ai"]


class MatchEngine:
    """Four-stage matcher with one-to-one assignment constraints."""

    def __init__(self, fuzzy_threshold: int = FUZZY_THRESHOLD,
                 ai_call: Optional[Callable] = None, ambiguity_margin: float = 3.0):
        if not 0 <= fuzzy_threshold <= 100:
            raise ValueError("fuzzy_threshold must be between 0 and 100")
        self.fuzzy_threshold = fuzzy_threshold
        self.ai_call = ai_call
        self.ambiguity_margin = max(0.0, float(ambiguity_margin))

    def match(self, expected_cols: List[str], actual_cols: List[str]) -> MatchReport:
        _validate_columns(expected_cols, "expected")
        _validate_columns(actual_cols, "actual")
        started = time.perf_counter()
        report = MatchReport()
        expected, actual = list(expected_cols), list(actual_cols)
        expected, actual = self._exact_match(expected, actual, report)
        expected, actual = self._normalized_match(expected, actual, report)
        expected, actual = self._fuzzy_match(expected, actual, report)
        if expected and actual and self.ai_call:
            expected, actual = self._ai_match(expected, actual, report)
        report.unmatched_expected = expected
        report.unmatched_actual = actual
        report.elapsed_seconds = time.perf_counter() - started
        logger.info(
            "Matching complete | exact=%d normalized=%d fuzzy=%d ai=%d unmatched_expected=%d unmatched_actual=%d elapsed=%.2fs",
            len(report.exact_matches), len(report.normalized_matches),
            len(report.fuzzy_matches), len(report.ai_matches), len(expected), len(actual),
            report.elapsed_seconds,
        )
        return report

    @staticmethod
    def _remove(remaining: List[str], matched: set) -> List[str]:
        return [value for value in remaining if value not in matched]

    def _exact_match(self, expected: List[str], actual: List[str], report: MatchReport):
        expected_set = set(expected)
        matched = set()
        for source in actual:
            if source in expected_set:
                report.matched.append(MatchResult(source, source, "exact", 1.0))
                matched.add(source)
        return self._remove(expected, matched), self._remove(actual, matched)

    def _normalized_match(self, expected: List[str], actual: List[str], report: MatchReport):
        expected_groups: Dict[str, List[str]] = defaultdict(list)
        actual_groups: Dict[str, List[str]] = defaultdict(list)
        for name in expected:
            key = normalize_column(name)
            if key:
                expected_groups[key].append(name)
        for name in actual:
            key = normalize_column(name)
            if key:
                actual_groups[key].append(name)

        matched_expected, matched_actual = set(), set()
        for key in sorted(set(expected_groups) & set(actual_groups)):
            targets, sources = expected_groups[key], actual_groups[key]
            if len(targets) != 1 or len(sources) != 1:
                warning = (f"Ambiguous normalized name '{key}': "
                           f"expected={targets}, actual={sources}; left unmatched")
                report.ambiguity_warnings.append(warning)
                logger.warning(warning)
                continue
            target, source = targets[0], sources[0]
            report.matched.append(MatchResult(source, target, "normalized", 0.99))
            matched_expected.add(target)
            matched_actual.add(source)
        return self._remove(expected, matched_expected), self._remove(actual, matched_actual)

    def _fuzzy_match(self, expected: List[str], actual: List[str], report: MatchReport):
        """Maximum-weight one-to-one assignment; ambiguous candidates stay unmatched."""
        if not expected or not actual:
            return expected, actual

        norm_expected = [normalize_column(name) for name in expected]
        norm_actual = [normalize_column(name) for name in actual]
        e_counts, a_counts = Counter(norm_expected), Counter(norm_actual)
        # Do not guess between columns that collapse to the same normalized form.
        eligible_e = [i for i, key in enumerate(norm_expected) if key and e_counts[key] == 1]
        eligible_a = [i for i, key in enumerate(norm_actual) if key and a_counts[key] == 1]
        if not eligible_e or not eligible_a:
            return expected, actual

        scores = [[float(fuzz.token_sort_ratio(norm_actual[ai], norm_expected[ei]))
                   for ei in eligible_e] for ai in eligible_a]
        try:
            from scipy.optimize import linear_sum_assignment
            import numpy as np
            row_indices, col_indices = linear_sum_assignment(-np.asarray(scores, dtype=float))
            assignments = list(zip(row_indices.tolist(), col_indices.tolist()))
        except ImportError:  # deterministic fallback if optional SciPy is unavailable
            edges = sorted(
                ((scores[r][c], r, c) for r in range(len(eligible_a)) for c in range(len(eligible_e))),
                reverse=True,
            )
            used_rows, used_cols, assignments = set(), set(), []
            for score, row, col in edges:
                if score < self.fuzzy_threshold:
                    break
                if row not in used_rows and col not in used_cols:
                    assignments.append((row, col))
                    used_rows.add(row)
                    used_cols.add(col)

        matched_expected, matched_actual = set(), set()
        for row, col in assignments:
            score = scores[row][col]
            if score < self.fuzzy_threshold:
                continue
            source_index, target_index = eligible_a[row], eligible_e[col]
            # Require a small margin over the next best candidate on both sides.
            source_alternatives = [v for j, v in enumerate(scores[row]) if j != col]
            target_alternatives = [scores[r][col] for r in range(len(scores)) if r != row]
            source_margin = score - max(source_alternatives, default=0.0)
            target_margin = score - max(target_alternatives, default=0.0)
            if (source_alternatives and source_margin < self.ambiguity_margin) or (
                target_alternatives and target_margin < self.ambiguity_margin
            ):
                report.ambiguity_warnings.append(
                    f"Ambiguous fuzzy candidate '{actual[source_index]}' → '{expected[target_index]}' "
                    f"(score {score:.1f}); left unmatched"
                )
                continue
            report.matched.append(MatchResult(
                actual[source_index], expected[target_index], "fuzzy",
                round(score / 100.0, 4), score,
            ))
            matched_expected.add(expected[target_index])
            matched_actual.add(actual[source_index])

        return self._remove(expected, matched_expected), self._remove(actual, matched_actual)

    def _ai_match(self, expected: List[str], actual: List[str], report: MatchReport):
        logger.info("Stage 4 – AI: %d expected / %d actual columns", len(expected), len(actual))
        try:
            proposed = self.ai_call(expected, actual)
        except Exception as exc:
            logger.warning("AI matching failed; retaining deterministic results: %s", exc)
            report.ambiguity_warnings.append(f"AI matching unavailable: {exc}")
            return expected, actual

        if proposed is None:
            return expected, actual
        if isinstance(proposed, dict):
            proposed = [MatchResult(source, target, "ai", 0.0)
                        for source, target in proposed.items()]
        if not isinstance(proposed, (list, tuple)):
            report.ambiguity_warnings.append("AI returned an unsupported mapping format")
            return expected, actual

        accepted_expected, accepted_actual = set(), set()
        for item in proposed:
            if not isinstance(item, MatchResult):
                report.ambiguity_warnings.append("AI returned a malformed mapping; item ignored")
                continue
            confidence = item.confidence
            if (not isinstance(item.source_col, str) or not isinstance(item.target_col, str)
                    or item.source_col not in actual or item.target_col not in expected
                    or item.source_col in accepted_actual or item.target_col in accepted_expected
                    or isinstance(confidence, bool) or not isinstance(confidence, (int, float))
                    or not math.isfinite(confidence) or not AI_CONFIDENCE_THRESHOLD <= confidence <= 1):
                report.ambiguity_warnings.append(
                    f"AI mapping '{item.source_col}' → '{item.target_col}' failed validation"
                )
                continue
            item.strategy = "ai"
            report.matched.append(item)
            accepted_actual.add(item.source_col)
            accepted_expected.add(item.target_col)
        return self._remove(expected, accepted_expected), self._remove(actual, accepted_actual)


def _validate_columns(columns: List[str], label: str) -> None:
    if not isinstance(columns, list):
        raise TypeError(f"{label}_cols must be a list")
    if any(not isinstance(value, str) or not value.strip() for value in columns):
        raise ValueError(f"{label} column names must be non-empty strings")
    duplicates = [name for name, count in Counter(columns).items() if count > 1]
    if duplicates:
        raise ValueError(f"Duplicate {label} column names are not supported: {duplicates}")