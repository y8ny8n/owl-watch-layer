"""scoring.py 단위테스트 — SQL/AI 없이 순수함수만 검증.
설계 핵심(설계문서 §3.2): 단일 신호는 혼자선 high 불가, 신호가 겹쳐야 high.
"""
from scoring import build_signals_json, score, severity


def test_single_signal_is_low_not_high():
    candidate = {
        "agent_id": 1,
        "fired": {"S6_night": {"hour": 23, "weekday": "Sat"}},
    }
    result = build_signals_json(candidate)

    assert result["risk_score"] == 10
    assert result["severity"] == "low"
    assert result["severity"] != "high"


def test_combined_signals_reach_high():
    candidate = {
        "agent_id": 2,
        "fired": {
            "S1_ext_spoof": {"file_name": "a.dwg", "dst_file_name": "a.txt"},
            "S6_night": {"hour": 23, "weekday": "Sat"},
            "S7_cross_channel": {"distinct_channels": 3, "total_allowed": 11},
        },
    }
    result = build_signals_json(candidate)

    assert result["risk_score"] == 65
    assert result["severity"] == "high"


def test_empty_fired_scores_zero():
    candidate = {"agent_id": 3, "fired": {}}
    result = build_signals_json(candidate)

    assert result["risk_score"] == 0
    assert result["severity"] == "low"
    assert result["signals"] == []


def test_signals_array_contains_registry_fields():
    candidate = {
        "agent_id": 4,
        "fired": {"S1_ext_spoof": {"file_name": "a.dwg", "dst_file_name": "a.txt"}},
    }
    result = build_signals_json(candidate)

    assert len(result["signals"]) == 1
    signal = result["signals"][0]
    assert signal["code"] == "S1_ext_spoof"
    assert signal["name"] == "확장자·이름 바꿔치기"
    assert signal["weight"] == 25
    assert signal["fired"] is True
    assert signal["evidence"] == {"file_name": "a.dwg", "dst_file_name": "a.txt"}
    assert signal["mitre"] == "T1027"


def test_score_and_severity_are_reused_directly():
    assert score([]) == 0
    assert severity(0) == "low"
    assert score(["S1_ext_spoof", "S6_night", "S7_cross_channel"]) == 65
    assert severity(65) == "high"
