# Refactor Backlog — Slice 1

> 작성일: TBD
> 산출 시점: Step 9 30분 슬롯 작업 후 갱신.
> 산식: `PriorityScore = (CostSaving × Frequency) / (RiskOfBreakage × TimeRequired)`
> TimeRequired 단위: 1=~5분, 5=~30분. 합산 ≤ 5 까지 Slice 1 적용.

---

## Candidates (PriorityScore 내림차순)

| #   | 항목 | CostSaving | Frequency | RiskOfBreakage | TimeRequired | PriorityScore | Slice 1? |
| --- | ---- | ---------- | --------- | -------------- | ------------ | ------------- | -------- |
| 1   | (예시) LLMClient cost 계산 if-elif 분기를 dict 매핑으로 정리 | 4 | 5 | 1 | 1 | 20.0 | YES |
| 2   | (예시) services/e1_garp.py prompt 합성 helper 분리 | 3 | 4 | 2 | 2 | 3.0 | YES |
| ... | ... | ... | ... | ... | ... | ... | ... |

> 위 표는 실제 발견 항목으로 교체. 후보 식별 도구: `pylint --enable=duplicate-code`, `radon cc -a`, `grep -n "TODO\|FIXME"`.

## Applied in Slice 1

(Step 9 적용 후 채움.)

| #   | 항목 | Commit | 회귀 결과 | 소요 시간 |
| --- | ---- | ------ | --------- | --------- |
|     |      |        |           |           |

## Deferred to Slice 2

(30분 한도 초과 + RiskOfBreakage가 큰 항목)

| #   | 항목 | 이연 사유 |
| --- | ---- | --------- |
|     |      |           |
