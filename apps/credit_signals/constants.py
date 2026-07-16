"""
credit_signals Phase 1 상수 (PR credit_signals Phase 1 §2).

수집 시리즈 목록은 하드코딩하지 말고 여기서 단일 소스로 관리한다.
스코프 = FRED 8 raw(6 Phase1 + BB·A P2-0) + 파생 2(compute-on-read, 원장 미적재).
불변 규칙 "6종 고정"은 P2-0에서 8종으로 명시 해제(재비준 = DECISIONS E). 추가는
동일 재비준 절차 없이 금지.
"""

# FRED 수집 대상 시리즈 (8종 = 6 raw Phase1 + BB·A P2-0 재비준, DECISIONS E)
FRED_SERIES = {
    "BAMLH0A0HYM2": {"name": "US HY OAS",  "unit": "pct"},
    "BAMLC0A0CM":   {"name": "US IG OAS",  "unit": "pct"},
    "BAMLC0A4CBBB": {"name": "BBB OAS",    "unit": "pct"},
    "BAMLH0A3HYC":  {"name": "CCC- OAS",   "unit": "pct"},
    "T10Y2Y":       {"name": "10Y-2Y",     "unit": "pct"},
    "VIXCLS":       {"name": "VIX Close",  "unit": "index"},
    "BAMLH0A1HYBB": {"name": "BB OAS",     "unit": "pct"},   # P2-0: CCC_MINUS_BB 감수 시리즈
    "BAMLC0A3CA":   {"name": "A OAS",      "unit": "pct"},   # P2-0: BBB_MINUS_A 감수 시리즈
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

# 파생 스프레드 키 (P2-0 실현). compute-on-read — 원장(MacroSeriesHistory)에는
# raw FRED만 적재하고 파생값은 적재하지 않는다(DECISIONS: 파생 compute-on-read).
# (피감 series_id, 감수 series_id) — 날짜 inner-join 후 스프레드 = 피감 − 감수.
DERIVED_SIGNAL_MAP = {
    "CCC_MINUS_BB": ("BAMLH0A3HYC", "BAMLH0A1HYBB"),  # CCC OAS − BB OAS
    "BBB_MINUS_A":  ("BAMLC0A4CBBB", "BAMLC0A3CA"),   # BBB OAS − A OAS
}
DERIVED_SERIES = {
    "CCC_MINUS_BB": {"name": "CCC−BB"},
    "BBB_MINUS_A":  {"name": "BBB−A"},
}

# 예약 키 실현됨(P2-0) — 더 이상 예약 없음.
RESERVED_SIGNAL_KEYS = ()

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
