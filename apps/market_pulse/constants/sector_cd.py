"""
apps/market_pulse/constants/sector_cd — 섹터 판단(CD) 4-상태 분류 상수·순수함수.

MP2-SECTOR-CD Slice 1. rel_strength × momentum_5d 사분면 분류.

판정 로직 단일소스: 이 함수만이 cd_state를 계산한다. payload builder(`_sector_detail`)가
유일한 소비처이며, FE·이메일 렌더러 등 2차 소비자는 서빙된 값만 표시(재계산 금지).

임계 상수 근거(D-SECTOR-CD, STEP 0 실측 2026-07-08):
  - rel_strength = sector_m1 − benchmark_m1 (벤치 대비 1일 모멘텀 차이 → 구조적 0 중심)
  - momentum_5d = 5일 수익률 (→ 0 중심)
  둘 다 부호가 의미(양=아웃퍼폼/상승, 음=언더퍼폼/하락) → baseline = 0.0.
  대안(1.0 비율 중심)은 두 값이 차분/수익률이라 기각.
"""

# 임계 baseline 단일소스 — 하드코딩 산재 금지. 이 상수만이 유일 출처.
CD_REL_STRENGTH_BASELINE = 0.0
CD_MOMENTUM_BASELINE = 0.0

# 4-상태 + 유보. FE 색 토큰·CD_STANCE 문구가 이 문자열을 키로 매핑한다.
CD_LEADING_STRENGTHENING = "leading_strengthening"  # 주도·강화
CD_LEADING_WEAKENING = "leading_weakening"  # 주도·둔화
CD_LAGGING_IMPROVING = "lagging_improving"  # 부진·개선
CD_LAGGING_DETERIORATING = "lagging_deteriorating"  # 부진·악화


def classify_cd_state(rel_strength, momentum_5d):
    """rel_strength × momentum_5d → CD 4-상태 문자열 (판단 유보 시 None).

    사분면 분류:
      rel > baseline AND mom  > baseline → leading_strengthening (주도·강화)
      rel > baseline AND mom <= baseline → leading_weakening     (주도·둔화)
      rel <= baseline AND mom > baseline → lagging_improving     (부진·개선)
      rel <= baseline AND mom <= baseline → lagging_deteriorating (부진·악화)

    경계 동률(== baseline)은 부등호대로 하위 상태 귀속 — 낙관 편향 금지.
    입력 어느 하나라도 None → None 반환(판단 유보, 값 발명 금지).
    """
    if rel_strength is None or momentum_5d is None:
        return None

    rel_lead = rel_strength > CD_REL_STRENGTH_BASELINE
    mom_up = momentum_5d > CD_MOMENTUM_BASELINE

    if rel_lead:
        return CD_LEADING_STRENGTHENING if mom_up else CD_LEADING_WEAKENING
    return CD_LAGGING_IMPROVING if mom_up else CD_LAGGING_DETERIORATING
