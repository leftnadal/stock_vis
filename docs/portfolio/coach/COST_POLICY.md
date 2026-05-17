# Cost Policy

> **목적**: LLM 비용 누적 추적 + 임계 위반 차단 정책
> **마지막 갱신**: 2026-05-17 (Slice 9 Step 0 #43)
> 최초 작성: Slice 5 Step 0 #γ1 (2026-05-07)

---

## §1. 임계값

### §1.1 누적 임계 (광의)

| 항목                      | 값        |
| ------------------------- | --------- |
| 누적 임계                 | **$3.00** |
| CostGuard 사전 경고 (80%) | $2.40     |
| Slice 10 재상향 트리거    | $2.80     |

### §1.2 슬라이스 cap (신규 §1.2 — Slice 9 #43 도입)

| 항목                  | 값                                                   |
| --------------------- | ---------------------------------------------------- |
| **슬라이스 단독 cap** | **$1.00**                                            |
| Cap 사전 경고 (80%)   | $0.80                                                |
| Cap 위반 시 처리      | 30분 이내 결정 사이클 진입 (재상향 vs 슬라이스 분리) |

**Cap 도입 근거**:

- Slice 8에서 사전 경고 $1.60 도달 후 matrix 실행 → 결과적으로 임계 직접 위반
- 누적 임계는 후행 지표 (이미 초과한 후 알게 됨)
- 슬라이스 cap은 선행 지표 (슬라이스 진입 전 예측 가능)
- 슬라이스 평균 $0.317 (S1~S8) + P95 $0.673 → cap $1.00은 P95 대비 +48.6% 안전 마진

### §1.3 단건 임계

| 모델   | 단건 임계 |
| ------ | --------- |
| Haiku  | $0.03     |
| Sonnet | $0.10     |

---

## §2. 갱신 이력

| 시점               | 임계      | 사유                                                                        |
| ------------------ | --------- | --------------------------------------------------------------------------- |
| Slice 1~6          | $1.00     | 초기 설정                                                                   |
| Slice 7            | $1.50     | Slice 7 #β2 -50% bias 보정 + Slice 8 예측 흡수                              |
| Slice 8            | $2.00     | Slice 7 0.6% 초과 + Slice 8 예측 흡수                                       |
| **Slice 9 (현재)** | **$3.00** | **Slice 8 #44 rationale 흡수 + Slice 10 mini-slice $0.22 흡수 (마진 7.9%)** |

---

## §3. 갱신 트리거

다음 조건 발생 시 임계 또는 cap 재상향 결정 사이클 진입:

- 누적 임계 80% 도달 (현재 $2.40)
- 슬라이스 cap 80% 도달 (현재 $0.80)
- 슬라이스 cap 직접 위반
- 단건 임계 위반 누적 3회

### §3.1 임계 도달 시 행동 (Slice 8 유지, Slice 9 cap 추가)

- 누적 ≥ 80% ($2.40): 경고 + Slice 매트릭스 축소 검토
- 누적 ≥ 90% ($2.70): 즉시 매트릭스 축소 + 부채 처리 우선
- 누적 ≥ 100% ($3.00): Slice 진행 중단, 정책 재검토
- **슬라이스 cap ≥ 80% ($0.80)**: 경고 + 슬라이스 남은 단계 비용 외삽 점검
- **슬라이스 cap ≥ 100% ($1.00)**: 슬라이스 진행 중단, 결정 사이클 진입

---

## §LLM budget (Slice 8 Part 1 #33, 2026-05-16 유지)

### 이중 카운터 정책

LLM 호출 횟수 한도를 두 차원으로 분리한다.

| 차원             | 한도    | 의미                                                                | 시점                              |
| ---------------- | ------- | ------------------------------------------------------------------- | --------------------------------- |
| **PER_INSTANCE** | **50**  | 단일 instance(스크립트 1회 실행, 야간 자동화 1 batch 등) 호출 한도 | `start_instance()` 호출 시 reset  |
| **PER_SLICE**    | **100** | 전체 slice (여러 instance 합산) 호출 한도                          | `reset_for_slice()` 호출 시 reset |

### 코드 인터페이스

```python
from portfolio.llm.cost_guard import CostGuard
from portfolio.llm.exceptions import BudgetExceededError

guard = CostGuard.get_instance()
guard.reset_slice("slice9_step0", max_calls=100)  # PER_SLICE=100

# 각 instance(스크립트) 진입 시
guard.start_instance()  # instance 카운터만 reset

# 매 LLM 호출 직전
try:
    guard.record_llm_call()  # 두 카운터 +1 + 두 check
    response = llm_client.call(prompt)
    guard.record_response(response.cost_usd, response.model)
    guard.record_cost(response.cost_usd)  # Slice 9 #43: cap+threshold 검증
except BudgetExceededError as e:
    if e.scope == "instance":
        ...
    elif e.scope == "slice":
        raise
```

### 한도 변경 이력

| 일자                     | 변경                                                            |
| ------------------------ | --------------------------------------------------------------- |
| 2026-05 (Slice 1~7)      | 단일 한도 50 (`max_calls=50`, `reset_slice(max_calls=50)`)      |
| 2026-05-16 (Slice 8 #33) | 이중 분리 PER_INSTANCE=50 / PER_SLICE=100                       |
| 2026-05-17 (Slice 9 #43) | 비용 차원 추가 — cap_per_slice $1.00, threshold $3.00 신설      |

---

## Appendix A. 슬라이스별 비용 추이

| Slice       | 단독 비용                  | 누적       |
| ----------- | -------------------------- | ---------- |
| S1          | $0.122                     | $0.122     |
| S2          | ~$0.05                     | ~$0.17     |
| S3          | ~$0.10                     | ~$0.27     |
| S4          | ~$0.05                     | ~$0.32     |
| S5          | $0.179                     | $0.764     |
| S6          | $0.115                     | $0.879     |
| S7          | $0.716                     | $1.595     |
| S8          | $0.453                     | $2.048     |
| **S9 예상** | **~$0.73** (#44 rationale) | **~$2.78** |

---

## Appendix B. Slice 8 사례 (Slice 9 Step 0 #43에서 추가)

### 상황

- Part 3 종결 시점: 누적 $2.0483 (임계 $2.00 +2.4% 위반)
- 사전 경고 $1.60는 Step 6 smoke 직후 도달 (Step 7 matrix 진입 전)
- Step 7 matrix 진행 → 결과적으로 임계 위반

### 학습

1. **사전 경고가 후행이었던 이유**: matrix 실행 의사결정이 사전 경고 도달 시점에 이미 사용자 회신 사이클 후였음. 결정 시점 ≠ 실행 시점.
2. **슬라이스 cap이 선행 지표**: 슬라이스 진입 전 cap 액수가 결정되므로, 진행 도중 결정 사이클 불필요.
3. **사용자 결정 (§5~§7 차단)**: 임계 위반 후 §5 rationale (~$0.74) 추가 진행 중단 결정 — 동일 패턴 회피 가치 증명.

### 적용

- Slice 9부터 슬라이스 단독 cap $1.00 도입
- Cap 위반 시 자동 차단 (`record_cost()`에서 `CostCapExceeded` raise)

---

## Appendix C. Slice 1~7 정책 (참고용 — Slice 5~8 변경 기록 보존)

| 일자       | 변경                                                                  |
| ---------- | --------------------------------------------------------------------- |
| 2026-05-07 | 초안 작성. Slice 5 Step 0 #γ1 부채 처리. 광의 단일 정책 채택          |
| 2026-05-11 | Slice 7 Part 1: 누적 광의 비용 임계 $1.00 → **$1.50** 갱신            |
| 2026-05-16 | Slice 8 Step 0-1 (D-1): 임계 $1.50 → **$2.00** 갱신                   |
| 2026-05-16 | Slice 8 Step 0-1 (#33): LLM budget 단일 50 → PER_INSTANCE/SLICE 분리  |
| 2026-05-17 | Slice 9 Step 0 (#43): 임계 $2.00 → **$3.00**, 슬라이스 cap $1.00 신설 |

### 단일 산출 정책 (Slice 5 #γ1)

누적 비용은 **광의** 단일 정책으로 산출한다. 메인 4스텝(Step 6/7/8/9) 외 모든 LLM 호출 비용을 포함:

- 진단 호출 (Gemini 진단 등)
- 재실행 호출 (smoke 재실행 등)
- 1차 손실 호출 (Step 8 실패 후 재시도 시 1차 비용)
- 백로그 처리 호출 (Step 9 슬롯 작업 호출 등)

### validation_report §5/§6 형식

- 표 제목: "광의 누적 비용"
- 메인 4스텝 비용은 _주석_(괄호)으로 1줄 표기 — 별도 표로 분리하지 않음
- 협의/광의 분리 표기 금지 (정의 일관성)

---

## Appendix D. Slice 7 Part 4 budget override 사례 (Slice 8 #33 보존)

### 사건 개요

- 시점: 2026-05-15 (Slice 7 Part 4 Phase B/C)
- 작업: `scripts/slice7/generate_rationale.py` 52건 sonnet rationale 생성
- 현상: 단일 instance에서 81회 호출 발생 → 기존 단일 한도 50 초과
- 회피: 호출 코드가 `reset_slice("slice7_part4_rationale", max_calls=80)`로 임시 한도 상향 → override
- 결과: 작업 완료, but 안전망 기능 무력화

### 근본 원인

- 단일 한도 50은 "작은 작업 (smoke 1~5회)"과 "큰 작업 (rationale 50+회)"을 한 정책으로 묶음
- 작업별 한도 상향 override가 정착되면 안전망의 의미 소실
- instance(스크립트 1회) 한도와 slice 전체 한도가 같아 격리 불가

### Slice 8 #33 처리

- **PER_INSTANCE=50**: 야간 자동화/매 instance가 폭주해도 50회에서 차단
- **PER_SLICE=100**: 여러 instance 합산해도 100회 한도 (rationale 52건 + smoke 등 흡수)
- `BudgetExceededError(scope="instance" or "slice")` raise 시 호출자가 적절히 대응 가능
