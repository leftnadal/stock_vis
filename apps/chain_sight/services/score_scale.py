"""RC 점수 눈금(scale) 단일 소스 — D-RC-SCALE (RC-A-1 PART 2).

RelationConfidence.truth_score·market_score 의 도메인을 [0,1] 단위 스케일로 통일한다
(score_version "3.0" 이후). 정규화 이전(version "2.1")은 [0,100] 계단 {0,35,60,85}였고,
소비처마다 /100·max·×0.60 로 눈금 가정이 제각각이라(RC-A-0 실측) 잠재 결함이 있었다.

★ 이 모듈이 "계단 3수치 + 현재 버전 + 구→신 변환"의 단일 출처다. 임계·writer 출력값·
  등급 경계는 전부 여기서 import 한다(리터럴 중복 정의 금지 — drift 방지).

계단 3수치는 writer 출력값이자 소비처 임계다(동일 수치의 이중 역할):
  0.85 = high/confirmed, 0.60 = medium/probable, 0.35 = low/weak(observed).
"""

# 현재 점수 버전. 이 값 이상(=이 값)인 행만 [0,1] 스케일이 보장된다.
SCORE_VERSION_CURRENT = "3.0"

# 계단 3종 (신뢰 등급 경계 = 소비처 임계 = writer 출력값)
GRADE_CONFIRMED_MIN = 0.85   # high / confirmed
GRADE_LIKELY_MIN = 0.60      # medium / probable
GRADE_OBSERVED_MIN = 0.35    # low / weak(observed)


def to_unit_scale(v):
    """구(舊) [0,100] 점수를 [0,1] 단위로 변환. 멱등·null 안전.

    규칙: v > 1.0 이면 /100 (구 계단 35/60/85 → 0.35/0.60/0.85),
          v <= 1.0 이면 무변경 (0, 그리고 이미 [0,1]인 오염값 0.5/0.6 = "PEER" 2행 보존).
    이미 변환된 값에 재적용해도 불변(멱등)이라 마이그레이션 재실행에 안전하다.
    None → None.
    """
    if v is None:
        return None
    return v / 100.0 if v > 1.0 else v


def apply_scale_normalization(RC):
    """전 행을 [0,1]·score_version="3.0"으로 정규화(멱등). 마이그레이션·테스트 공용 단일 소스.

    RC = RelationConfidence 모델 클래스(런타임) 또는 historical 모델(apps.get_model).
    to_unit_scale와 동일 규칙을 bulk F-expression으로 수행:
      truth_score/market_score > 1.0 인 행만 /100 (구 [0,100] 계단 → [0,1]),
      이미 [0,1]인 값(0·오염 0.5/0.6)은 무접촉. 이후 전 행 score_version="3.0".
    멱등: 재실행 시 >1.0 필터가 비어 no-op. 반환 = 변경 행수 dict.
    """
    from django.db.models import F

    truth_scaled = RC.objects.filter(truth_score__gt=1.0).update(
        truth_score=F("truth_score") / 100.0
    )
    market_scaled = RC.objects.filter(market_score__gt=1.0).update(
        market_score=F("market_score") / 100.0
    )
    versioned = RC.objects.update(score_version=SCORE_VERSION_CURRENT)
    return {
        "truth_scaled": truth_scaled,
        "market_scaled": market_scaled,
        "versioned": versioned,
    }
