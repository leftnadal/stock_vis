"""detect_truncation 캡 감지 유틸 단위 테스트 (EVT-IMPL-1 STEP 3-2).

mock 픽스처만 — 실 FMP 호출 없음(3-3). 필드는 SURVEY-0/2 실측 기준.
케이스: 90일 tail 절단 / 45일 정상 / 정확히 4000 / 빈 응답 / sparse-front.
"""
from packages.shared.api_request.providers.fmp.calendar_cap import (
    FMP_CALENDAR_ROW_CAP,
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
    def test_90d_tail_truncation_hits_cap(self):
        """90일 요청인데 4000행·뒤 16일만(11-03~11-18) = 절단 True."""
        rows = _rows([f"2026-11-{day:02d}" for day in range(3, 19)] * 250)  # 4000행
        assert len(rows) == FMP_CALENDAR_ROW_CAP
        assert detect_truncation("2026-08-20", "2026-11-18", rows) is True

    def test_45d_normal_full_span(self):
        """45일 요청·2302행·from(08-20)부터 커버 = 정상 False."""
        rows = _rows(["2026-08-20", "2026-09-01", "2026-10-02"] + ["2026-09-15"] * 2299)
        assert len(rows) == 2302
        assert detect_truncation("2026-08-20", "2026-10-04", rows) is False

    def test_exact_cap_count_is_truncation(self):
        rows = _rows(["2026-08-20"] * FMP_CALENDAR_ROW_CAP)
        assert detect_truncation("2026-08-20", "2026-11-18", rows) is True

    def test_over_cap_count_is_truncation(self):
        rows = _rows(["2026-08-20"] * (FMP_CALENDAR_ROW_CAP + 5))
        assert detect_truncation("2026-08-20", "2026-11-18", rows) is True

    def test_empty_response_not_truncation(self):
        assert detect_truncation("2026-08-20", "2026-11-18", []) is False

    def test_front_clip_detected_even_under_cap(self):
        """행 수는 캡 미만이지만 가장 이른 반환일이 요청 from보다 늦음 = 앞 절단 True."""
        rows = _rows(["2026-11-10", "2026-11-15", "2026-11-18"])
        assert detect_truncation("2026-08-20", "2026-11-18", rows) is True

    def test_covers_from_date_not_truncation(self):
        rows = _rows(["2026-08-20", "2026-09-10"])
        assert detect_truncation("2026-08-20", "2026-11-18", rows) is False

    def test_unparseable_dates_fall_back_safely(self):
        rows = _rows([None, "", "garbage"])
        # 파싱 가능 날짜 0 → 절단 판정 불가 → False (캡 미도달)
        assert detect_truncation("2026-08-20", "2026-11-18", rows) is False
