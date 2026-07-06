"""
P1-BUILD: 추천 캐러셀 필드 + 발행 로그(IssuanceLog) 테스트.

- baker._derive_confidence: signal-strength formula v1 (D-P1-CONF)
- baker._build_recommendations: top-N 정렬·제외·placeholder 골격 (D-P1-RECPROD)
- baker._build_dashboard_json: recommendations additive, 기존 6키 IDENTICAL
- baker._write_issuance_log: grain 멱등 write, user_id=None (D-P1-GRAIN·D-SCHEMA)
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from packages.shared.stocks.services.eod_json_baker import EODJSONBaker

pytestmark = pytest.mark.unit


# ───────────────────────────────────────────────
# _derive_confidence (D-P1-CONF, formula v1)
# ───────────────────────────────────────────────

@pytest.mark.parametrize(
    "score,expected",
    [
        (0.8, "high"),
        (0.5, "high"),
        (-0.6, "high"),      # magnitude 기반
        (0.3, "medium"),
        (-0.25, "medium"),
        (0.1, "low"),
        (0.0, "low"),
        (None, "low"),
    ],
)
def test_derive_confidence_v1(score, expected):
    baker = EODJSONBaker()
    assert baker._derive_confidence(score) == expected


# ───────────────────────────────────────────────
# _build_recommendations (top-N, 정렬, 제외, placeholder)
# ───────────────────────────────────────────────

def _sig(symbol, primary, cs):
    return {"stock_id": symbol, "tag_details": {"primary": primary}, "composite_score": cs}


def test_build_recommendations_sorts_by_abs_composite_score():
    baker = EODJSONBaker()
    recs = baker._build_recommendations(
        [_sig("AAA", "V1", 0.4), _sig("BBB", "P2", -0.8), _sig("CCC", "S1", 0.6)]
    )
    assert [r["ticker"] for r in recs] == ["BBB", "CCC", "AAA"]
    assert [r["rank"] for r in recs] == [1, 2, 3]


def test_build_recommendations_excludes_no_primary_tag():
    baker = EODJSONBaker()
    recs = baker._build_recommendations(
        [_sig("AAA", "V1", 0.9), _sig("NOPE", None, 0.99)]
    )
    assert [r["ticker"] for r in recs] == ["AAA"]


def test_build_recommendations_respects_top_n():
    baker = EODJSONBaker()
    data = [_sig(f"S{i}", "V1", 1.0 - i * 0.01) for i in range(20)]
    recs = baker._build_recommendations(data)
    assert len(recs) == baker.RECOMMEND_TOP_N


def test_build_recommendations_placeholder_and_fields():
    baker = EODJSONBaker()
    rec = baker._build_recommendations([_sig("AAA", "V1", 0.55)])[0]
    assert rec["signal_tag"] == "V1"
    assert rec["confidence"] == "high"
    assert rec["conf_ver"] == 1
    assert rec["composite_score"] == 0.55
    # placeholder 골격 (LLM 후속)
    assert rec["thesis"] is None
    assert rec["perspectives"] == {
        "technical": None, "fundamental": None, "news_context": None,
    }
    assert rec["risk"] is None


# ───────────────────────────────────────────────
# _build_dashboard_json IDENTICAL (기존 6키 불변 + recommendations additive)
# ───────────────────────────────────────────────

def test_dashboard_json_keeps_six_keys_and_adds_recommendations():
    baker = EODJSONBaker()
    market_summary = {"headline": "x"}
    pipeline_log = MagicMock(run_id="rid", status="success",
                             total_duration_seconds=1.0, stages={})
    sentinel_cards = [{"id": "sentinel"}]

    with patch.object(baker, "_preload_mini_charts"), \
         patch.object(baker, "_group_signals_into_cards", return_value=sentinel_cards):
        result = baker._build_dashboard_json(
            date(2026, 2, 25), [_sig("AAA", "V1", 0.7)], market_summary, pipeline_log
        )

    # 기존 6키가 순서·값 그대로 (IDENTICAL) + recommendations만 additive 말미
    assert list(result.keys()) == [
        "generated_at", "trading_date", "is_stale",
        "market_summary", "signal_cards", "pipeline_meta", "recommendations",
    ]
    assert result["signal_cards"] is sentinel_cards      # 기존 계약 불변
    assert result["market_summary"] is market_summary
    assert result["trading_date"] == "2026-02-25"
    assert result["recommendations"][0]["ticker"] == "AAA"


# ───────────────────────────────────────────────
# _write_issuance_log (grain 멱등, user_id=None)
# ───────────────────────────────────────────────

@pytest.mark.django_db
def test_write_issuance_log_writes_and_is_idempotent():
    from packages.shared.stocks.models import IssuanceLog, Stock

    Stock.objects.create(symbol="AAA", stock_name="Alpha")
    Stock.objects.create(symbol="BBB", stock_name="Beta")
    baker = EODJSONBaker()
    recs = baker._build_recommendations(
        [_sig("AAA", "V1", 0.8), _sig("BBB", "P2", -0.6)]
    )
    target = date(2026, 2, 25)

    written = baker._write_issuance_log(recs, target)
    assert written == 2
    assert IssuanceLog.objects.count() == 2

    row = IssuanceLog.objects.get(stock__symbol="AAA")
    assert row.signal_tag == "V1"
    assert row.confidence == "high"
    assert row.conf_ver == 1
    assert row.rank == 1
    assert row.user_id is None          # bake-time, per-user 아님
    assert row.published_at is not None

    # 재실행 = grain 멱등 (중복 행 0)
    baker._write_issuance_log(recs, target)
    assert IssuanceLog.objects.count() == 2


@pytest.mark.django_db
def test_write_issuance_log_skips_unknown_ticker():
    from packages.shared.stocks.models import IssuanceLog

    baker = EODJSONBaker()
    recs = baker._build_recommendations([_sig("GHOST", "V1", 0.9)])
    written = baker._write_issuance_log(recs, date(2026, 2, 25))
    assert written == 0
    assert IssuanceLog.objects.count() == 0
