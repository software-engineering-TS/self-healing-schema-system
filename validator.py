"""Post-mapping validation for schema reconciliation."""
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List

from logger import logger


@dataclass
class ValidationReport:
    is_valid: bool = True
    missing_expected: List[str] = field(default_factory=list)
    duplicate_mappings: Dict[str, List[str]] = field(default_factory=dict)
    unmapped_actual: List[str] = field(default_factory=list)
    extra_actual: List[str] = field(default_factory=list)
    duplicate_expected: List[str] = field(default_factory=list)
    duplicate_actual: List[str] = field(default_factory=list)
    invalid_mappings: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "missing_expected": self.missing_expected,
            "duplicate_mappings": self.duplicate_mappings,
            "unmapped_actual": self.unmapped_actual,
            "extra_actual": self.extra_actual,
            "duplicate_expected": self.duplicate_expected,
            "duplicate_actual": self.duplicate_actual,
            "invalid_mappings": self.invalid_mappings,
            "warnings": self.warnings,
            "errors": self.errors,
        }


class SchemaValidator:
    def __init__(self, expected_cols: List[str], mapping: Dict[str, str], actual_cols: List[str]):
        self.expected_cols = list(expected_cols)
        self.mapping = dict(mapping)
        self.actual_cols = list(actual_cols)

    def validate(self) -> ValidationReport:
        report = ValidationReport()
        report.duplicate_expected = [c for c, n in Counter(self.expected_cols).items() if n > 1]
        report.duplicate_actual = [c for c, n in Counter(self.actual_cols).items() if n > 1]
        if report.duplicate_expected:
            report.errors.append(f"Duplicate expected column names: {report.duplicate_expected}")
        if report.duplicate_actual:
            report.errors.append(f"Duplicate incoming column names: {report.duplicate_actual}")

        for source, target in self.mapping.items():
            if source not in self.actual_cols or target not in self.expected_cols:
                report.invalid_mappings.append(f"{source!r} → {target!r} references an unknown column")
        if report.invalid_mappings:
            report.errors.extend(report.invalid_mappings)

        target_sources = defaultdict(list)
        for source, target in self.mapping.items():
            target_sources[target].append(source)
        report.duplicate_mappings = {target: sources for target, sources in target_sources.items() if len(sources) > 1}
        if report.duplicate_mappings:
            report.errors.append(f"Duplicate target mappings: {report.duplicate_mappings}")

        mapped_targets = set(self.mapping.values())
        mapped_sources = set(self.mapping.keys())
        report.missing_expected = [c for c in self.expected_cols if c not in mapped_targets]
        if report.missing_expected:
            report.errors.append(f"Missing expected columns: {report.missing_expected}")

        report.unmapped_actual = [c for c in self.actual_cols if c not in mapped_sources]
        report.extra_actual = [c for c in report.unmapped_actual if c not in self.expected_cols]
        if report.unmapped_actual:
            report.warnings.append(
                f"Unmapped incoming columns are excluded from the expected-schema output: {report.unmapped_actual}"
            )
        report.is_valid = not report.errors
        for message in report.errors:
            logger.warning(message)
        for message in report.warnings:
            logger.info(message)
        logger.info("Validation complete | valid=%s missing=%d duplicates=%d unmapped=%d",
                    report.is_valid, len(report.missing_expected), len(report.duplicate_mappings),
                    len(report.unmapped_actual))
        return report