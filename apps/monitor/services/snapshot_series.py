"""MonitorSnapshot 기반 점수 정본 시계열 (MON-P2B T1, read-only).

**동결 기록(MonitorSnapshot)을 단일 원천**으로 스트립 델타·일지 스냅샷을 산출한다
(D-MON-P2B ⑴ — 값·델타·일지 3원 소스 혼재 해소). 일지는 "시스템이 그날 실제로
기록한 값"만 담으므로 로직 변경에도 과거가 불변(기록 무결성).

대비: sparkline(`score_series`)는 IndicatorReading에서 매 호출 재산출하는 **추세 곡선**
(기록 아님)으로 목록 카드·StateBandSparkline이 계속 소비한다 — 무접촉. 여기 시계열은
그와 별개 원천(스냅샷)이다.
"""
from apps.monitor.models.monitoring import MonitorSnapshot

WINDOW_DEFAULT = 30  # 최근 스냅샷 수


def snapshot_series(monitor, window=WINDOW_DEFAULT):
    """최근 `window` 스냅샷의 {asof, score, delta} 시계열(asof_date 오름차순).

    delta = 직전 스냅샷 overall_score 대비 차. 산출 가능하면 항상 값(**±0.0 포함** —
    반올림 0 무표시로 인한 정보 은닉 제거), 전체 첫 스냅샷(직전 부재)만 None.
    window 경계 첫 점도 window 밖 직전 스냅샷 대비 delta를 갖도록 전체에서 계산 후 자른다.

    반환: {
        "series": [{"asof": iso, "score": float, "delta": float|None}, ...],
        "window": int,
    }
    """
    rows = list(
        MonitorSnapshot.objects.filter(monitor=monitor)
        .order_by("asof_date")
        .values_list("asof_date", "overall_score")
    )

    series_all = []
    prev = None
    for asof_date, score in rows:
        delta = None if prev is None else round(score - prev, 4)
        series_all.append(
            {"asof": asof_date.isoformat(), "score": score, "delta": delta}
        )
        prev = score

    series = series_all[-window:] if window else series_all
    return {"series": series, "window": window}
