"""
credit_signals Phase 1 상수 (PR credit_signals Phase 1 §2).

수집 시리즈 목록은 하드코딩하지 말고 여기서 단일 소스로 관리한다.
Phase 1 스코프 = FRED 6종 고정. BB·A 등급(CCC_MINUS_BB / BBB_MINUS_A)은
Phase 2 이후이므로 수집 목록을 6→8로 늘리는 것은 금지.
"""

# FRED 수집 대상 시리즈 (6종 고정 — §10 금지사항: 추가 금지)
FRED_SERIES = {
    "BAMLH0A0HYM2": {"name": "US HY OAS",  "unit": "pct"},
    "BAMLC0A0CM":   {"name": "US IG OAS",  "unit": "pct"},
    "BAMLC0A4CBBB": {"name": "BBB OAS",    "unit": "pct"},
    "BAMLH0A3HYC":  {"name": "CCC- OAS",   "unit": "pct"},
    "T10Y2Y":       {"name": "10Y-2Y",     "unit": "pct"},
    "VIXCLS":       {"name": "VIX Close",  "unit": "index"},
}

# signal_key → FRED series_id 매핑.
# signal_key는 Thesis Layer E가 나중에 `HY_OAS_Z > 2` 형태로 참조할 안정 계약이다.
# 순서를 바꾸거나 키를 rename하지 말 것 (하위 소비처 계약).
SIGNAL_SERIES_MAP = {
    "HY_OAS":      "BAMLH0A0HYM2",
    "IG_OAS":      "BAMLC0A0CM",
    "BBB_OAS":     "BAMLC0A4CBBB",
    "CCC_OAS":     "BAMLH0A3HYC",
    "CURVE_10Y2Y": "T10Y2Y",
    "VIX":         "VIXCLS",
}

# 예약 키 (Phase 1 미계산 — BB·A 시리즈가 수집 목록에 없어서 계산 불가).
#   "CCC_MINUS_BB"  = CCC OAS − BB OAS   (Phase 2: BB 시리즈 수집 후)
#   "BBB_MINUS_A"   = BBB OAS − A OAS    (Phase 2: A 시리즈 수집 후)
# 이번 PR에서는 키만 예약하며 CreditSignalState를 만들지 않는다.
RESERVED_SIGNAL_KEYS = ("CCC_MINUS_BB", "BBB_MINUS_A")

Z_WINDOW_DAYS = 756          # 3년 거래일 근사 (3년 롤링 z-score)
MAD_FLOOR = 1e-6             # Robust Z(MAD) 분모 과폭발 방지 floor (Thesis Control 규약과 동형)
MIN_OBSERVATIONS = 60        # 콜드스타트 하한 — 60개 미만이면 z=null, grade=gray
HY_OAS_CRISIS_BP = 800       # 문헌 기반 절대 임계 (bp). z와 별개로 red 판단에 사용
MAD_CONSISTENCY = 1.4826     # normal consistency factor = 1 / 0.6745 (Thesis indicator_scorer 동형)

# grade 임계 (compute) — §4 grade 규칙
Z_YELLOW = 1.0               # 1 ≤ z < 2 → yellow
Z_ORANGE = 2.0               # z ≥ 2    → orange (HY_OAS는 절대값 조건 시 red 승격)

# 일별 증분 수집 창 (최근 N일). 주말/공휴일 결측 흡수를 위해 여유를 둔다.
INGEST_WINDOW_DAYS = 10

# verify 태스크: 최신 관측이 이 일수보다 오래되면 결측으로 간주 (FRED 발행 지연 흡수)
INGEST_STALE_DAYS = 4

GRADE_CHOICES = (
    ("gray", "gray"),
    ("yellow", "yellow"),
    ("orange", "orange"),
    ("red", "red"),
)
