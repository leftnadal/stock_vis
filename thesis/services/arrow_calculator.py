"""Arrow Calculator: score -> degree/color/label 변환 (수학 모델 v2.3.2, Section 3.5)"""

from thesis.services.indicator_scorer import score_indicator_from_model

# 설계 문서 Section 5.4: 색상 5단계
COLOR_BANDS = [
    (0, 45, '#2563EB'),     # 강한 지지
    (45, 75, '#60A5FA'),    # 지지
    (75, 105, '#9CA3AF'),   # 중립
    (105, 135, '#FB923C'),  # 약화
    (135, 180, '#DC2626'),  # 강한 반박
]

# 설계 문서 Section 5.4: 라벨 7단계
LABEL_BANDS = [
    (0, 30, '강하게 지지'),
    (30, 60, '지지하는 중'),
    (60, 80, '살짝 지지'),
    (80, 100, '중립'),
    (100, 120, '살짝 약화'),
    (120, 150, '약화 중'),
    (150, 180, '강하게 반박'),
]


def score_to_degree(score):
    """score(-1~1) -> degree(0~180). score=1->0, score=0->90, score=-1->180."""
    return 90 - (score * 90)


def degree_to_color(degree):
    """degree -> hex color string."""
    for low, high, color in COLOR_BANDS:
        if low <= degree < high:
            return color
    return '#DC2626'  # 180


def degree_to_label(degree):
    """degree -> 한글 라벨 (7단계)."""
    for low, high, label in LABEL_BANDS:
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
