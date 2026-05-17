# Specificity Patterns — rationale 텍스트 자동 분류 patterns

> **목적**: E4 답변의 "구체성 부족" 비율을 자동 측정 (Slice 7 75% → Slice 8 <30% 목표)
> **사용처**: Slice 8 Part 3 §5 rationale 28건 자동 카운트
> **재사용**: Slice 9 이후 동일 KPI 측정 시 본 patterns 재사용
> **작성일**: 2026-05-17 (Slice 8 Part 3 §0.4)

---

## P1: 종목별 현재가/지표 언급

**정규식 또는 키워드**: `(현재가|주가|PE|PEG|ROIC|P/E|시가)` 1회 이상 등장
**5점 조건**: 종목명 + 지표값 함께 등장 (예: "삼성전자 PE 12.5")

## P2: 임계값/기준점 명시

**키워드**: `(이상|이하|초과|미만|보다 (높|낮))` AND 숫자 1회 이상
**5점 조건**: 비교 기준 명확 (예: "PE 15 이상은 부담", "ROIC 10% 미만 우려")

## P3: 액션 동사 (buy/sell/hold/축소/확대/유지)

**키워드**: `(매수|매도|보유|축소|확대|편입|제외|유지)` 1회 이상
**5점 조건**: 종목명 + 액션 동사 직접 연결 (예: "삼성전자 축소 검토")

## P4: 구체 수치 임계값

**키워드**: 숫자 + (%|배|원|달러) AND 동일 문장 내 종목명/지표명
**5점 조건**: 정량 의사결정 가능 수준 (예: "현금 비중 25% → 20%로 5%p 축소")

## P5: 기간/시점 명시

**키워드**: `(분기|반기|연간|YoY|QoQ|최근 \d+(년|개월|일))` 1회 이상
**5점 조건**: 시계열 비교 또는 의사결정 시점 명시

---

## 측정 룰

- **구체성 score** = P1~P5 중 등장 patterns 개수 (0~5)
- **"구체성 부족"** 판정: score ≤ 2
- **목표**: 28건 중 "구체성 부족" 비율 < 30% (8건 이하)
- **mismatch 처리**: manual eval에서 score 불일치 시 manual 우선, patterns docs 갱신 등록

---

## 구현 위치

- patterns count 헬퍼: `portfolio/tests/slice8/helpers/specificity_count.py`
- count 호출: `count_patterns(text: str) -> int` (0~5 반환)
- 단위 테스트: `portfolio/tests/slice8/test_specificity_patterns.py`
