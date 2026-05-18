# Slice 11 Part 2 Step 2 — Schema 매핑표 (KPI 2)

> 신규 통합 output schema 설계. Part 1 `commentary_input.py` 구조 미러.

## 1. 기존 7 필드 → Base / sub class 매핑

지시서 §1.2의 매핑표를 기준으로 sub class 분배 확정.

| 기존 필드 (Slice 8 Part 2 도입)                | 위치       | 신규 위치                             |
| ---------------------------------------------- | ---------- | ------------------------------------- |
| `summary` (str, min_length=1)                  | E1~E6 공통 | **Base**                              |
| `key_observations` (list[str])                 | E1~E6 공통 | **Base**                              |
| `confidence` (Literal["high","medium","low"])  | E1~E6 공통 | **Base**                              |
| `action_items` (list[ActionItem])              | E1/E3/E5   | **각 sub class** (E1, E3, E5)         |
| `risk_flags` (list[str])                       | E1/E3/E6   | **각 sub class** (E1, E3, E6)         |
| `metrics_table` (str, deprecated wrapper #21)  | E1/E2      | **각 sub class** (E1, E2, deprecated) |
| `quoted_metrics` (dict)                        | E2/E5/E6   | **각 sub class** (E2, E5, E6)         |

**원칙** (Part 1 미러):
- 6 진입점 전부 공통 → Base
- 일부만 공통 → 해당 sub class 각각 정의 (DRY 깨지더라도 명시성 우선)
- `ActionItem`은 모듈 안에 보존 (호출자 4건 호환)

## 2. ActionItem 보존

기존 정의 **변경 0**. 필드/제약/Literal 그대로 흡수:

| 필드        | 타입                                                                | 비고                          |
| ----------- | ------------------------------------------------------------------- | ----------------------------- |
| title       | str (min_length=1, max_length=80)                                   |                               |
| description | str (min_length=10, max_length=300)                                 |                               |
| priority    | Literal["high","medium","low"]                                      | default="medium"              |
| category    | Optional[Literal["rebalance","review","monitor","research"]]        | default=None                  |

## 3. 신규 sub class 별 필드

지시서 §1.4 골격을 그대로 채택.

| Sub class   | Base 상속 필드 (3종)                  | 추가 필드                                              |
| ----------- | ------------------------------------- | ------------------------------------------------------ |
| `E1Output`  | summary / key_observations / confidence | `action_items`, `risk_flags`, `metrics_table` (#21)   |
| `E2Output`  | 동일                                  | `quoted_metrics`, `metrics_table` (#21)                |
| `E3Output`  | 동일                                  | `action_items`, `risk_flags`                            |
| `E4Output`  | 동일                                  | (없음 — 대화 Q&A는 base만)                              |
| `E5Output`  | 동일                                  | `action_items`, `quoted_metrics`                        |
| `E6Output`  | 동일                                  | `risk_flags`, `quoted_metrics`                          |

## 4. schema 설정 (Part 1 동일)

```python
model_config = ConfigDict(frozen=True, extra="forbid")
```

## 5. Registry

```python
COMMENTARY_OUTPUT_CLASSES: dict[str, type[CommentaryOutputBase]] = {
    "e1": E1Output, "e2": E2Output, "e3": E3Output,
    "e4": E4Output, "e5": E5Output, "e6": E6Output,
}
```

Part 1 `COMMENTARY_INPUT_CLASSES` 미러 — input/output 1:1 대응.

## 6. 기존 class 이름 vs 신규 class 이름

기존 `commentary_output.py`에는 `ActionItem`만 존재. 다른 출력 schema (E1Response, E2DiagnosticCard, E6ComparisonResponse 등)는 `portfolio/schemas/llm_outputs.py`에 별도 존재 (legacy 진입점 service용, **Part 2 scope 외**).

신규 `E1Output`~`E6Output`은 **Slice 11 trio 통합 진입점용 신규 schema**. 기존 legacy schema 대체 아님.

| 신규 class       | 의미                                |
| ---------------- | ----------------------------------- |
| `CommentaryOutputBase` | 6 진입점 공통 base            |
| `E1Output`       | A2 통합 시연 — E1 GARP commentary  |
| `E2Output`       | A2 통합 시연 — E2 종합 진단        |
| `E3Output`       | A2 통합 시연 — E3 집중도 분석      |
| `E4Output`       | A2 통합 시연 — E4 대화 Q&A         |
| `E5Output`       | A2 통합 시연 — E5 추출             |
| `E6Output`       | A2 통합 시연 — E6 분석엔진         |

기존 legacy class와 이름 충돌 없음 (예: `E2DiagnosticCard` vs `E2Output`).

## 7. 매핑 완전성 검증 (KPI 2)

- 7 필드 모두 신규 구조에 1:1 대응: ✓ (`summary`/`key_observations`/`confidence`/`action_items`/`risk_flags`/`metrics_table`/`quoted_metrics`)
- ActionItem 모두 흡수: ✓ (변경 0)
- 누락 0 / 추가 0: ✓

## 결론

매핑표 확정. Step 3 리팩토링 진입 준비 완료.
