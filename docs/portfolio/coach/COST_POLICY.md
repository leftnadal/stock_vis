# 누적 비용 산출 정책

> 작성: Slice 5 Step 0 (#γ1 부채 처리, 2026-05-07)
> 적용 대상: Slice 5 이후 모든 validation_report

## 단일 산출 정책

누적 비용은 **광의** 단일 정책으로 산출한다. 메인 4스텝(Step 6/7/8/9) 외 모든 LLM 호출 비용을 포함:

- 진단 호출 (Gemini 진단 등)
- 재실행 호출 (smoke 재실행 등)
- 1차 손실 호출 (Step 8 실패 후 재시도 시 1차 비용)
- 백로그 처리 호출 (Step 9 슬롯 작업 호출 등)

## 누적 baseline (Slice 1~4 광의)

| 시점         | 광의 누적 |
| ------------ | --------- |
| Slice 1 종결 | $0.137    |
| Slice 2 종결 | $0.327    |
| Slice 3 종결 | $0.428    |
| Slice 4 종결 | $0.585    |

## validation_report §5/§6 형식

- 표 제목: "광의 누적 비용"
- 메인 4스텝 비용은 _주석_(괄호)으로 1줄 표기 — 별도 표로 분리하지 않음
- 협의/광의 분리 표기 금지 (정의 일관성)

## 변경 이력

| 일자       | 변경                                                         |
| ---------- | ------------------------------------------------------------ |
| 2026-05-07 | 초안 작성. Slice 5 Step 0 #γ1 부채 처리. 광의 단일 정책 채택 |
| 2026-05-11 | Slice 7 Part 1: 누적 광의 비용 임계 $1.00 → **$1.50** 갱신   |
| 2026-05-16 | Slice 8 Step 0-1 (D-1): 임계 $1.50 → **$2.00** 갱신 (Slice 7 종결 시 $1.595로 0.6% 초과 상태 해소) |
| 2026-05-16 | Slice 8 Step 0-1 (#33): LLM budget 단일 50 → **PER_INSTANCE=50 / PER_SLICE=100** 분리 |

---

## Cost Threshold Policy (Slice 8 갱신, 2026-05-16)

### 누적 광의 비용 임계: **$2.00** (이전 $1.50)

#### 갱신 근거 (정량)

- 7슬라이스 누적 비용: **$1.595** (Slice 1~7 광의 합산, 평균 $0.228 per slice)
- Slice 7 단독 비용: $0.49 (E4 multi-turn 외삽이 진입 시 예상 $0.32~0.42보다 +20% 상회)
- Slice 8 추정 비용: **$0.30~0.50** (insight trio: schema + fixture + prompt 변경, LLM 호출 trim 가능)
- Slice 9~10 추정: **$0.30~0.40** × 2 = **$0.60~0.80**
- 안전 마진 (10%): **$0.18**
- **총 합산: $1.595 + $0.50 + $0.80 + $0.18 ≈ $3.07** → Slice 10까지 안전한 임계 산정
- 결론: $1.50은 Slice 8 진입 전 초과, $2.00은 Slice 9 중반까지 안전, **$2.00 채택**
- **Slice 8 진입 시 $2.00 채택** (Slice 10 진입 전 재검토)

#### 임계 도달 시 행동

- 누적 ≥ 80% ($1.60): 경고 + Slice 매트릭스 축소 검토
- 누적 ≥ 90% ($1.80): 즉시 매트릭스 축소 + 부채 처리 우선
- 누적 ≥ 100% ($2.00): Slice 진행 중단, 정책 재검토

#### 누적 현황 (참고)

| 시점         | 광의 누적 | 임계 대비 |
| ------------ | --------- | --------- |
| Slice 6 종결 | $0.879    | 43.95% (구 임계 58.6%) |
| Slice 7 종결 | $1.595    | 79.75% (구 임계 106.3%, 0.6% 초과 → 갱신으로 해소) |

---

## §LLM budget (Slice 8 Part 1 #33, 2026-05-16)

### 이중 카운터 정책

LLM 호출 횟수 한도를 두 차원으로 분리한다.

| 차원 | 한도 | 의미 | 시점 |
|------|------|------|------|
| **PER_INSTANCE** | **50** | 단일 instance(스크립트 1회 실행, 야간 자동화 1 batch 등) 호출 한도 | `start_instance()` 호출 시 reset |
| **PER_SLICE** | **100** | 전체 slice (여러 instance 합산) 호출 한도 | `reset_for_slice()` 호출 시 reset |

### 코드 인터페이스

```python
from portfolio.llm.cost_guard import CostGuard
from portfolio.llm.exceptions import BudgetExceededError

guard = CostGuard.get_instance()
guard.reset_slice("slice8_part1", max_calls=100)  # PER_SLICE=100

# 각 instance(스크립트) 진입 시
guard.start_instance()  # instance 카운터만 reset

# 매 LLM 호출 직전
try:
    guard.record_llm_call()  # 두 카운터 +1 + 두 check
    response = llm_client.call(prompt)
    guard.record_response(response.cost_usd, response.model)
except BudgetExceededError as e:
    if e.scope == "instance":
        # 다음 instance 진입 시 start_instance() 후 재시도 가능
        ...
    elif e.scope == "slice":
        # slice 전체 한도 도달 → 작업 중단
        raise
```

### 임계 변경 이력

| 일자 | 변경 |
|------|------|
| 2026-05 (Slice 1~7) | 단일 한도 50 (`max_calls=50`, `reset_slice(max_calls=50)`) |
| 2026-05-16 (Slice 8 #33) | 이중 분리 PER_INSTANCE=50 / PER_SLICE=100 |

---

## Appendix A — Slice 7 Part 4 budget override 사례

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
- `BudgetExceededError(scope="instance" or "slice")` raise 시 호출자가 적절히 대응 가능 (instance scope면 `start_instance()` 후 재시도, slice scope면 작업 중단)
