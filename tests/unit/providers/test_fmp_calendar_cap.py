"""detect_truncation 캡 감지 유틸 단위 테스트 (EVT-IMPL-1 STEP 3-2 · EVT-IMPL-2 §2 재설계).

재설계: 절단 = count >= FMP_CALENDAR_ROW_CAP 단독. 앞 지연(min_date > from+grace)은
span_anomaly 경고(절단 아님). mock 픽스처만 — 실 FMP 호출 없음.
"""
import logging

from packages.shared.api_request.providers.fmp.calendar_cap import (
    FMP_CALENDAR_ROW_CAP,
    SPAN_ANOMALY_GRACE_DAYS,
    detect_truncation,
)


def _rows(dates):
    """SURVEY-0 실측 earnings 필드 형태의 mock 행 생성."""
    return [
        {
            "date": d,
            "symbol": f"SYM{i}",
            "epsEstimated": 1.0,
            "epsActual": None,
            "revenueEstimated": 1000,
            "revenueActual": None,
            "lastUpdated": "2026-08-20",
        }
        for i, d in enumerate(dates)
    ]


class TestDetectTruncation:
    def test_cap_reached_is_truncation(self):
        """행 수 == 하드캡 → 절단 True (유일 조건)."""
        rows = _rows(["2026-08-20"] * FMP_CALENDAR_ROW_CAP)
        assert detect_truncation("2026-08-20", "2026-11-18", rows) is True

    def test_over_cap_is_truncation(self):
        rows = _rows(["2026-08-20"] * (FMP_CALENDAR_ROW_CAP + 5))
        assert detect_truncation("2026-08-20", "2026-11-18", rows) is True

    def test_45d_normal_full_span_not_truncation(self):
        """45일·2302행·from부터 커버 = 정상 False."""
        rows = _rows(["2026-08-20", "2026-09-01", "2026-10-02"] + ["2026-09-15"] * 2299)
        assert len(rows) == 2302
        assert detect_truncation("2026-08-20", "2026-10-04", rows) is False

    def test_weekend_start_window_not_truncation(self):
        """주말 시작 창(min_date=from+3, 소량) — 앞 지연이지만 grace 이내 → False, 경고 없음."""
        rows = _rows(["2026-08-24", "2026-08-25", "2026-08-27"])  # from=08-21(금)+3=월
        assert detect_truncation("2026-08-21", "2026-10-04", rows) is False

    def test_empty_response_not_truncation(self):
        assert detect_truncation("2026-08-20", "2026-11-18", []) is False

    def test_front_clip_under_cap_is_not_truncation(self):
        """앞 절단처럼 보여도 캡 미도달이면 절단 아님(재설계) — False."""
        rows = _rows(["2026-11-10", "2026-11-15", "2026-11-18"])
        assert detect_truncation("2026-08-20", "2026-11-18", rows) is False


class TestSpanAnomalyWarning:
    def test_large_front_lag_emits_span_anomaly_warning(self, caplog):
        """앞 지연 > grace → span_anomaly 경고 발화(단, 절단 아님 = False)."""
        rows = _rows(["2026-11-10", "2026-11-15"])  # from=08-20 → 지연 82일 » grace 5
        with caplog.at_level(logging.WARNING):
            result = detect_truncation("2026-08-20", "2026-11-18", rows)
        assert result is False
        assert any("span_anomaly" in r.message for r in caplog.records)

    def test_within_grace_no_warning(self, caplog):
        """앞 지연 <= grace → 경고 없음."""
        lag = SPAN_ANOMALY_GRACE_DAYS  # 정확히 grace = 경고 없음(> 조건)
        rows = _rows([f"2026-08-{20 + lag:02d}"])
        with caplog.at_level(logging.WARNING):
            detect_truncation("2026-08-20", "2026-10-04", rows)
        assert not any("span_anomaly" in r.message for r in caplog.records)

    def test_unparseable_dates_no_crash_no_truncation(self):
        rows = _rows([None, "", "garbage"])
        assert detect_truncation("2026-08-20", "2026-11-18", rows) is False
