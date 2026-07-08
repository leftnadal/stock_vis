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


# ───────────────────────────────────────────────
# _verify_issuance (D-HC-ISSUANCE — Stage 7 자가검증)
# ───────────────────────────────────────────────

@pytest.mark.django_db
def test_verify_issuance_ok_when_rows_match_n():
    from packages.shared.stocks.models import Stock

    Stock.objects.create(symbol="AAA", stock_name="Alpha")
    Stock.objects.create(symbol="BBB", stock_name="Beta")
    baker = EODJSONBaker()
    target = date(2026, 2, 25)
    recs = baker._build_recommendations(
        [_sig("AAA", "V1", 0.8), _sig("BBB", "P2", -0.6)]
    )
    baker._write_issuance_log(recs, target)

    verified = baker._verify_issuance(recs, target)
    assert verified == {"expected": 2, "written": 2, "ok": True}


@pytest.mark.django_db
def test_verify_issuance_flags_mismatch_and_logs_error():
    """인위 불일치: 종목 미존재로 write < N → ok=False + logger.error(경보). bake 중단 아님."""
    from packages.shared.stocks.models import Stock

    Stock.objects.create(symbol="AAA", stock_name="Alpha")  # BBB 미존재
    baker = EODJSONBaker()
    target = date(2026, 2, 25)
    recs = baker._build_recommendations(
        [_sig("AAA", "V1", 0.8), _sig("BBB", "P2", -0.6)]
    )
    baker._write_issuance_log(recs, target)  # AAA만 write (BBB skip)

    with patch("packages.shared.stocks.services.eod_json_baker.logger") as mock_log:
        verified = baker._verify_issuance(recs, target)

    assert verified == {"expected": 2, "written": 1, "ok": False}
    assert mock_log.error.called  # 경보 발생


def test_verify_issuance_query_failure_returns_zero_written():
    """테이블 부재 등 조회 실패(#46) → written=0, ok=False(경보). 예외 전파 없음."""
    baker = EODJSONBaker()
    recs = [{"ticker": "AAA"}, {"ticker": "BBB"}]

    with patch(
        "packages.shared.stocks.models.IssuanceLog.objects.filter",
        side_effect=RuntimeError("no such table: stocks_issuance_log"),
    ), patch("packages.shared.stocks.services.eod_json_baker.logger") as mock_log:
        verified = baker._verify_issuance(recs, date(2026, 2, 25))

    assert verified == {"expected": 2, "written": 0, "ok": False}
    assert mock_log.exception.called or mock_log.error.called


# ───────────────────────────────────────────────
# bake() 통합 — pipeline_meta additive-within + 7키 IDENTICAL + write 실패 완주
# ───────────────────────────────────────────────

def _bake_patches(baker, captured, tmp_dir):
    """bake()의 파일/DB 무거운 곳을 패치. dashboard.json 내용은 captured에 포착."""
    baker.TMP_DIR = tmp_dir  # 실 signals_tmp 무접촉

    def fake_write_json(path, data):
        if path.name == "dashboard.json":
            captured["dashboard"] = data

    return [
        patch.object(baker, "_preload_mini_charts"),
        patch.object(baker, "_group_signals_into_cards", return_value=[]),
        patch.object(baker, "_write_json", side_effect=fake_write_json),
        patch.object(baker, "_build_card_jsons", return_value=0),
        patch.object(baker, "_build_stock_jsons", return_value=0),
        patch.object(baker, "_build_meta_json", return_value={}),
        patch.object(baker, "_atomic_swap"),
        patch.object(baker, "_upsert_snapshot", return_value=MagicMock(pk=1)),
    ]


@pytest.mark.django_db
def test_bake_injects_issuance_verified_and_keeps_keys(tmp_path):
    from contextlib import ExitStack

    from packages.shared.stocks.models import Stock

    Stock.objects.create(symbol="AAA", stock_name="Alpha")
    baker = EODJSONBaker()
    captured: dict = {}
    pipeline_log = MagicMock(
        run_id="rid", status="success", total_duration_seconds=1.0, stages={}
    )

    with ExitStack() as stack:
        for p in _bake_patches(baker, captured, tmp_path / "tmp"):
            stack.enter_context(p)
        baker.bake(
            date(2026, 2, 25), [_sig("AAA", "V1", 0.7)], {"headline": "x"}, pipeline_log
        )

    dashboard = captured["dashboard"]
    # 7 top-level 키 IDENTICAL(순서·집합 불변)
    assert list(dashboard.keys()) == [
        "generated_at", "trading_date", "is_stale",
        "market_summary", "signal_cards", "pipeline_meta", "recommendations",
    ]
    pm = dashboard["pipeline_meta"]
    # 기존 4 subfield 불변 + issuance_verified additive-within
    assert set(pm) == {
        "run_id", "status", "total_duration_seconds", "stages", "issuance_verified",
    }
    assert pm["run_id"] == "rid" and pm["status"] == "success"
    assert pm["issuance_verified"] == {"expected": 1, "written": 1, "ok": True}


@pytest.mark.django_db
def test_bake_completes_and_flags_when_issuance_write_raises(tmp_path):
    """#46: 발행 로그 write 예외 → bake 완주(파일 서빙) + issuance_verified.ok=False 경보."""
    from contextlib import ExitStack

    from packages.shared.stocks.models import Stock

    Stock.objects.create(symbol="AAA", stock_name="Alpha")
    baker = EODJSONBaker()
    captured: dict = {}
    pipeline_log = MagicMock(
        run_id="rid", status="success", total_duration_seconds=1.0, stages={}
    )

    with ExitStack() as stack:
        for p in _bake_patches(baker, captured, tmp_path / "tmp"):
            stack.enter_context(p)
        # write는 예외, 검증 조회는 0행 → ok=False
        stack.enter_context(
            patch.object(
                baker, "_write_issuance_log", side_effect=RuntimeError("boom")
            )
        )
        result = baker.bake(
            date(2026, 2, 25), [_sig("AAA", "V1", 0.7)], {"headline": "x"}, pipeline_log
        )

    # bake는 완주 (files_written 반환, 예외 전파 없음)
    assert result["files_written"] >= 1
    # dashboard.json은 정상 서빙 + 경보 필드
    pm = captured["dashboard"]["pipeline_meta"]
    assert pm["issuance_verified"]["ok"] is False
    assert pm["issuance_verified"]["expected"] == 1
    assert pm["issuance_verified"]["written"] == 0
