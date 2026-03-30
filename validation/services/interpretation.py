"""
Rule-based 해석 텍스트 생성

- generate_summary_text: 종합 한줄 요약
- generate_metric_interpretation: 개별 지표 해석
- generate_leader_summary: 업종 리더 대비 비교 요약
"""

from validation.services.category_signal_calculator import CATEGORY_DISPLAY


def generate_summary_text(category_signals: list) -> str:
    """종합 한줄 요약 (설계서 섹션 3.1)"""
    green_cats = [s for s in category_signals if s.signal == 'green']
    red_cats = [s for s in category_signals if s.signal == 'red']
    gray_cats = [s for s in category_signals if s.signal == 'gray']

    parts = []

    if len(green_cats) >= 2:
        top2 = sorted(green_cats, key=lambda c: float(c.score or 0), reverse=True)[:2]
        n1 = CATEGORY_DISPLAY.get(top2[0].category, top2[0].category)
        n2 = CATEGORY_DISPLAY.get(top2[1].category, top2[1].category)
        parts.append(f"높은 {n1}과(와) {n2}")
    elif len(green_cats) == 1:
        n = CATEGORY_DISPLAY.get(green_cats[0].category, green_cats[0].category)
        parts.append(f"{n}이(가) 강점")

    if red_cats:
        n = CATEGORY_DISPLAY.get(red_cats[0].category, red_cats[0].category)
        parts.append(f"{n} 부분 주의 필요")

    if gray_cats:
        parts.append(f"{len(gray_cats)}개 카테고리 해석 제한")

    if len(green_cats) >= 5:
        return "전반적으로 양호한 재무 체질. " + ". ".join(parts) + "."
    elif len(red_cats) >= 2:
        return ". ".join(parts) + ". 심층 분석 권장."
    elif not green_cats and not red_cats:
        return "대부분 지표가 중립 구간. 뚜렷한 강점/약점 없음."
    else:
        return ". ".join(parts) + "."


def generate_metric_interpretation(
    metric_code: str, higher_is_better: bool,
    percentile_rank: float, trend: str,
    value_status: str, benchmark_confidence: str,
    not_applicable_reason: str = '',
) -> str:
    """개별 지표 해석 (설계서 섹션 3.3)"""
    if value_status == 'not_applicable':
        return not_applicable_reason or '해당 없음'
    if value_status == 'missing':
        return '데이터가 제공되지 않아 비교할 수 없습니다.'

    parts = []

    # 상대 위치
    if percentile_rank is not None:
        pct = float(percentile_rank)
        if pct >= 75:
            parts.append(f"peer 상위 {100 - pct:.0f}%에 위치")
        elif pct <= 25:
            parts.append(f"peer 하위 {pct:.0f}%에 위치")
        else:
            parts.append("업종 중앙값 수준")

    # 추세
    if trend == 'improving':
        parts.append("최근 3년간 개선 추세")
    elif trend == 'declining':
        parts.append("최근 3년간 하락 추세")
    elif trend:
        parts.append("최근 3년간 안정적")

    # benchmark 신뢰도 경고
    if benchmark_confidence in ('low', 'limited'):
        parts.append("비교 표본이 적어 해석에 주의 필요")

    # value_status 경고
    if value_status == 'unstable':
        parts.append("값 변동이 크므로 추세 해석에 주의")

    # 방향성
    direction = "높을수록" if higher_is_better else "낮을수록"
    parts.append(f"({direction} 좋은 지표)")

    return ". ".join(parts) + "."


def determine_trend(history_values: list[float]) -> str:
    """최근 3년 추세 판정"""
    if len(history_values) < 3:
        return ''
    recent_3 = history_values[-3:]
    if recent_3[-1] > recent_3[0] * 1.05:
        return 'improving'
    elif recent_3[-1] < recent_3[0] * 0.95:
        return 'declining'
    return 'stable'


def generate_leader_summary(advantages: list, disadvantages: list) -> str:
    """업종 리더 대비 비교 요약 (설계서 섹션 3.5)"""
    total = len(advantages) + len(disadvantages)
    if total == 0:
        return "비교 데이터 부족."

    parts = [f"{total}개 비교 지표 중 {len(advantages)}개 우위."]

    if advantages:
        adv_cats = list(dict.fromkeys(a.get('category', '') for a in advantages))
        parts.append(f"강점: {', '.join(CATEGORY_DISPLAY.get(c, c) for c in adv_cats[:3])}.")

    if disadvantages:
        dis_cats = list(dict.fromkeys(d.get('category', '') for d in disadvantages))
        parts.append(f"약점: {', '.join(CATEGORY_DISPLAY.get(c, c) for c in dis_cats[:3])}.")

    return " ".join(parts)
