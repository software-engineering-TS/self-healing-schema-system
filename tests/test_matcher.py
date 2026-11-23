import pytest
from matcher import MatchEngine, MatchResult


def test_exact_and_normalized_matching():
    report = MatchEngine(ai_call=None).match(
        ["patient_id", "first name"], ["patient_id", "first_name"]
    )
    assert report.mapping == {"patient_id": "patient_id", "first_name": "first name"}
    assert len(report.exact_matches) == 1
    assert len(report.normalized_matches) == 1


def test_normalization_collision_is_not_silently_overwritten():
    report = MatchEngine(ai_call=None).match(
        ["patient-id", "patient_id"], ["patient id"]
    )
    assert report.mapping == {}
    assert len(report.ambiguity_warnings) == 1
    assert report.unmatched_expected == ["patient-id", "patient_id"]


def test_fuzzy_matching_uses_one_to_one_assignments():
    report = MatchEngine(fuzzy_threshold=70, ai_call=None).match(
        ["customer_name", "customer_address"], ["customer_nam", "customer_addres"]
    )
    assert len(report.mapping) == 2
    assert len(set(report.mapping.values())) == 2


def test_low_similarity_is_not_matched():
    report = MatchEngine(fuzzy_threshold=90, ai_call=None).match(
        ["customer_identifier"], ["weather_condition"]
    )
    assert not report.matched


def test_ai_results_are_scope_and_confidence_checked():
    def fake_ai(expected, actual):
        return [
            MatchResult("incoming_a", "target_a", "ai", 0.95),
            MatchResult("incoming_a", "target_b", "ai", 0.99),
            MatchResult("outside", "target_b", "ai", 0.99),
            MatchResult("incoming_b", "target_b", "ai", float("nan")),
        ]

    report = MatchEngine(ai_call=fake_ai).match(
        ["target_a", "target_b"], ["incoming_a", "incoming_b"]
    )
    assert report.mapping == {"incoming_a": "target_a"}
    assert report.unmatched_expected == ["target_b"]
    assert report.unmatched_actual == ["incoming_b"]


def test_ai_exception_falls_back_without_crashing():
    def broken_ai(*_):
        raise RuntimeError("offline")

    report = MatchEngine(ai_call=broken_ai).match(["semantic target"], ["source"])
    assert report.mapping == {}
    assert report.unmatched_expected == ["semantic target"]
    assert any("AI matching unavailable" in item for item in report.ambiguity_warnings)


@pytest.mark.parametrize("columns", [["x", "x"], [" ", "y"], [None]])
def test_invalid_column_names_rejected(columns):
    with pytest.raises((TypeError, ValueError)):
        MatchEngine(ai_call=None).match(columns, ["source"])


def test_ai_confidence_below_threshold_is_rejected():
    def weak_ai(expected, actual):
        return [MatchResult(actual[0], expected[0], "ai", 0.2)]
    report = MatchEngine(ai_call=weak_ai).match(["semantic target"], ["source"])
    assert not report.matched
    assert report.unmatched_expected == ["semantic target"]


def test_ai_callback_with_unhashable_fields_is_ignored():
    def malformed_ai(expected, actual):
        return [MatchResult([], [], "ai", 0.9)]
    report = MatchEngine(ai_call=malformed_ai).match(["target"], ["source"])
    assert not report.matched