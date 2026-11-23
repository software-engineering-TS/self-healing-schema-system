import pandas as pd
import pytest

from utils import extract_json, normalize_column, read_expected_schema, validate_csv_header
from validator import SchemaValidator


def test_normalize_column_common_separators_and_unicode():
    assert normalize_column("  RADIUS__Mean-Δ  ") == "radius mean δ"


def test_extract_json_from_fenced_and_noisy_text():
    assert extract_json('```json\n{"mappings": []}\n```') == {"mappings": []}
    assert extract_json('answer: {"ok": true} thanks') == {"ok": True}
    assert extract_json("not json") is None


def test_read_expected_schema_checks_empty_and_duplicate_values():
    with pytest.raises(ValueError):
        read_expected_schema(pd.DataFrame())
    with pytest.raises(ValueError, match="duplicate"):
        read_expected_schema(pd.DataFrame({"schema": ["id", "id"]}))


def test_validator_reports_missing_and_unmapped_columns():
    report = SchemaValidator(["id", "name"], {"raw_id": "id"}, ["raw_id", "extra"]).validate()
    assert not report.is_valid
    assert report.missing_expected == ["name"]
    assert report.unmapped_actual == ["extra"]
    assert report.extra_actual == ["extra"]
    assert report.warnings


def test_validator_rejects_mapping_to_unknown_target():
    report = SchemaValidator(["id"], {"raw": "unknown"}, ["raw"]).validate()
    assert not report.is_valid
    assert report.invalid_mappings


def test_csv_header_validation_rejects_duplicate_and_blank_headers():
    with pytest.raises(ValueError, match="duplicate"):
        validate_csv_header(b"id,id\n1,2\n")
    with pytest.raises(ValueError, match="empty column"):
        validate_csv_header(b"id,\n1,2\n")

def test_csv_header_validation_accepts_utf8_bom():
    assert validate_csv_header(b"\xef\xbb\xbfid,name\n1,A\n") == ["id", "name"]