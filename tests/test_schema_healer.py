import pandas as pd
import pytest

from matcher import MatchResult
from schema_healer import _ai_match_columns, _reconstruct, heal_schema


def test_sample_dataset_deterministic_pipeline():
    expected = ["person_id", "diagnosis", "radius mean", "texture mean",
                "perimeter mean", "area mean", "smoothness mean", "compactness mean",
                "concavity mean", "concave points mean", "symmetry mean", "fractal dimension mean"]
    incoming = pd.read_csv("sample_incoming_data.csv")
    result = heal_schema(incoming, expected, ai_call=None)
    assert result.strategy_summary == {"exact": 0, "normalized": 2, "fuzzy": 8, "ai": 0, "unmatched": 2}
    assert list(result.healed_df.columns) == expected
    assert len(result.healed_df) == len(incoming)
    assert result.validation_report.missing_expected == ["person_id", "diagnosis"]
    assert result.validation_report.unmapped_actual == ["id", "diag"]


def test_reconstruction_preserves_values_and_order():
    frame = pd.DataFrame({"old_b": [2, 4], "old_a": [1, 3]})
    healed = _reconstruct(frame, ["a", "b", "missing"], {"old_a": "a", "old_b": "b"})
    assert list(healed.columns) == ["a", "b", "missing"]
    assert healed["a"].tolist() == [1, 3]
    assert healed["b"].tolist() == [2, 4]
    assert healed["missing"].isna().all()


def test_heal_rejects_duplicate_incoming_headers():
    frame = pd.DataFrame([[1, 2]], columns=["x", "x"])
    with pytest.raises(ValueError, match="duplicate column"):
        heal_schema(frame, ["x"], ai_call=None)


def test_heal_rejects_duplicate_expected_headers():
    with pytest.raises(ValueError, match="duplicate column"):
        heal_schema(pd.DataFrame({"x": [1]}), ["x", "x"], ai_call=None)


def test_ai_mapping_response_validated(monkeypatch):
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"response": '{"mappings":['
                    '{"actual":"a","expected":"x","confidence":0.9},'
                    '{"actual":"b","expected":"y","confidence":"high"},'
                    '{"actual":"unknown","expected":"x","confidence":0.99}]}' }

    monkeypatch.setattr("schema_healer._call_ollama_with_retry", lambda payload: Response().json())
    results = _ai_match_columns(["x", "y"], ["a", "b"])
    assert [(r.source_col, r.target_col) for r in results] == [("a", "x")]


def test_invalid_ai_callback_item_does_not_break_pipeline():
    def fake_ai(expected, actual):
        return ["not a MatchResult", MatchResult("src", "target", "ai", 1.4)]
    result = heal_schema(pd.DataFrame({"src": [1]}), ["target"], ai_call=fake_ai)
    assert result.mapping == {}
    assert result.healed_df["target"].isna().all()


def test_reconstruct_rejects_duplicate_targets():
    with pytest.raises(ValueError, match="multiple source"):
        _reconstruct(pd.DataFrame({"a": [1], "b": [2]}), ["x"], {"a": "x", "b": "x"})


def test_default_ai_is_skipped_when_ollama_is_offline(monkeypatch):
    monkeypatch.setattr("schema_healer.check_ollama", lambda: False)
    result = heal_schema(pd.DataFrame({"unrelated": [1]}), ["semantic_target"])
    assert not result.match_report.ai_matches
    assert any("Ollama unavailable" in warning for warning in result.validation_report.warnings)