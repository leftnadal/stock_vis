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

from decimal import Decimal

# 임계 baseline 단일소스 — 하드코딩 산재 금지. 이 상수만이 유일 출처.
CD_REL_STRENGTH_BASELINE = 0.0
CD_MOMENTUM_BASELINE = 0.0

# CD-STAB Slice A′ (D-CD-XAXIS-SCOPE): 판단 x축 = 5일 상대수익. 5거래일 룩백.
#   저장 0(서빙 시점 파생) — bench(SPY) 5일 수익률은 payload builder가 서빙 시 계산.
CD_REL_STRENGTH_5D_LOOKBACK = 5


def derive_rel_strength_5d(momentum_5d, bench_5d_return):
    """5일 상대수익 = 섹터 5일 수익률 − 벤치(SPY) 5일 수익률.

    A′ 판단 x축(D-CD-XAXIS-SCOPE). 기존 rel_strength(1일 차분)와 별개 additive 필드.
    어느 하나 None → None 반환(판단 유보, 값 발명·보간 금지 — 규칙 #5).
    bench가 소급 부족(초기 5거래일)·close 결측이면 bench_5d_return None으로 들어옴.
    """
    if momentum_5d is None or bench_5d_return is None:
        return None
    return Decimal(momentum_5d) - Decimal(bench_5d_return)

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


# CD-STAB Slice B — 2일 히스테리시스 (D-CD-STAB, D-CD-STATE-SEMANTICS).
CD_HYSTERESIS_CONFIRM_DAYS = 2  # 후보 사분면이 이 연속 거래일수 유지되면 공식 전환.


def resolve_official_cd_state(raw_sequence):
    """저장 raw 상태 시퀀스(거래일 오름차순) → 공식(확정) 상태 시퀀스.

    무상태 리플레이(규칙 #2): 저장 히스토리를 결정론적으로 재생. `classify_cd_state`는
    무변경 — 이 함수는 그 출력 시퀀스만 소비하는 별도 순수 함수(규칙 #3).

    규칙 명세(D-CD-STAB):
      - 시드: 시퀀스 첫 non-None raw = 초기 공식 상태.
      - 전환: 후보 사분면(≠현재 공식)이 CD_HYSTERESIS_CONFIRM_DAYS(2) 연속 거래일 유지될 때만
        공식 전환. 전환 인정일 = 2일째.
      - 후보 리셋: 유지 중 후보가 다른 사분면으로 바뀌면 카운터 리셋(새 후보 1일차).
      - raw가 공식과 같은 날: 후보 카운터 리셋.
      - raw None인 날: 후보 카운터 리셋 + 공식 상태 유지(유보값으로 전환 안 함 — 방어 명세,
        현재 momentum_5d non-nullable이라 dead path).

    반환: raw_sequence와 동일 길이의 공식 상태 리스트. payload는 마지막 원소(현재 공식)를 소비.
    """
    official = None
    candidate = None
    streak = 0
    out = []
    for raw in raw_sequence:
        if official is None:
            # 시드: 첫 non-None을 초기 공식으로.
            if raw is not None:
                official = raw
            candidate = None
            streak = 0
        elif raw is None:
            # 유보값으로 전환 안 함 — 후보만 리셋, 공식 유지.
            candidate = None
            streak = 0
        elif raw == official:
            candidate = None
            streak = 0
        elif raw == candidate:
            streak += 1
            if streak >= CD_HYSTERESIS_CONFIRM_DAYS:
                official = raw  # 2연속 확정 → 이 날(2일째) 전환.
                candidate = None
                streak = 0
        else:
            # 새 후보(1일차).
            candidate = raw
            streak = 1
        out.append(official)
    return out
