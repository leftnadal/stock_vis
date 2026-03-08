"""Arrow Calculator: score -> degree/color/label 변환 (수학 모델 v2.3.2, Section 3.5)"""

from thesis.services.indicator_scorer import score_indicator_from_model

# 수학 모델 Section 3.5 COLOR_MAP
COLOR_MAP = [
    (0, 36, '#2563EB', '강하게 지지'),
    (36, 72, '#60A5FA', '지지하는 편'),
    (72, 108, '#9CA3AF', '중립'),
    (108, 144, '#FB923C', '약화하는 편'),
    (144, 180, '#DC2626', '강하게 반박'),
]


def score_to_degree(score):
    """score(-1~1) -> degree(0~180). score=1->0, score=0->90, score=-1->180."""
    return 90 - (score * 90)


def degree_to_color(degree):
    """degree -> hex color string."""
    for low, high, color, _ in COLOR_MAP:
        if low <= degree < high:
            return color
    return '#DC2626'  # 180


def degree_to_label(degree):
    """degree -> 한글 라벨."""
    for low, high, _, label in COLOR_MAP:
        if low <= degree < high:
            return label
    return '강하게 반박'  # 180


def calculate_indicator_arrow(indicator, as_of_date=None):
    """
    ThesisIndicator 하나에 대한 전체 화살표 계산.

    Returns:
        dict with score, degree, color, label, is_extreme_vol, raw_z,
              effective_window, is_neutral_mad, is_sufficient
    """
    result = score_indicator_from_model(indicator, as_of_date)

    score = result['score']
    degree = score_to_degree(score)
    color = degree_to_color(degree)
    label = degree_to_label(degree)

    # paused/override 특수 라벨
    if result.get('is_paused'):
        label = '일시정지됨'
        color = '#9CA3AF'
    elif result.get('is_override'):
        label = f'{label} (수동)'
    elif not result.get('is_sufficient', True):
        label = '데이터 부족'
        color = '#9CA3AF'
    elif result.get('is_neutral_mad'):
        label = '변동 없음'
        color = '#9CA3AF'

    return {
        'score': score,
        'degree': round(degree, 1),
        'color': color,
        'label': label,
        'is_extreme_vol': result.get('is_extreme_vol', False),
        'raw_z': result.get('raw_z', 0.0),
        'effective_window': result.get('effective_window', 0),
        'is_neutral_mad': result.get('is_neutral_mad', False),
        'is_sufficient': result.get('is_sufficient', False),
    }
