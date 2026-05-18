# Slice 11 Step 0 지시서 — A2 통합 시연 trio 5-Part 진입

> **슬라이스 성격**: full slice (trio 5-Part β 패턴, S8 정착)
> **진입점**: A2 = 1 portfolio × E1~E6 6 진입점 종합 commentary
> **Step 0 단독 예상**: 회귀 +13~18 / 비용 $0~$0.05 / LLM 0~5/50
> **Slice 11 전체 예상**: 회귀 512→537~547 (+25~35) / 비용 $0.40~0.60 / 누적 $2.78~2.98

---

## 0. 사전 결정 (확정)

| 결정               | 채택                                           | 핵심                                   |
| ------------------ | ---------------------------------------------- | -------------------------------------- |
| D-1 진입점         | A. E4+E6 통합 시연 (tie-breaker)               | 메모리 흐름 + 진입점 진도 부재 해소    |
| A sub-option       | A2. 1 portfolio × E1~E6 종합 commentary        | 가장 큰 production-ready demo          |
| D-2 Step 9 슬롯    | b. #51 + #52 (Step 0에 묶음 처리)              | Slice 10 자연 후속                     |
| D-3 비용 임계      | ii. $3.00 → $4.00 상향                         | 비용 패턴($1→$1.5→$2→$3→$4) 일관       |
| D-4 E6 의존성      | a. mock fixture 일관 유지                      | 5슬라이스 정책 보존                    |
| D-5 Part 구조      | β. trio 5-Part (Step0/Part1/Part2/Part3/Part4) | S8 패턴 정착                           |
| Slice 11 cap       | $1.00 유지 (Slice 9 정책)                      | 5-Part 분산 마진 충분                  |
| KPI 9c (자연 추가) | #48 v3 첫 실측 검증 (Part 3 smoke 시점)        | count_tokens vs 실제 input_tokens 대조 |

---

## 1. trio 5-Part 전체 로드맵

| Part       | 작업                                                           | 산출물 핵심     | 회귀 분배 | 비용 분배  |
| ---------- | -------------------------------------------------------------- | --------------- | --------- | ---------- |
| **Step 0** | #51 output estimator + #52 messages 보존 + E6 mock + 임계 상향 | 13건            | +13~18    | $0~$0.05   |
| Part 1     | 6 진입점 통합 input schema (TimeSeriesContext 확장)            | schema + tests  | +5~7      | $0         |
| Part 2     | 6 진입점 통합 output schema + #41 자연 close                   | schema + tests  | +5~7      | $0         |
| Part 3     | prompt builder 6종 + smoke + matrix 12콜 (haiku/sonnet × 6)    | prompt + matrix | +5~7      | $0.30~0.50 |
| Part 4     | manual eval + 종결 (KPI 9c 검증 + 부채 close)                  | eval + closing  | +0~3      | $0.10      |

**Step 0 (현재 지시서)는 trio 5-Part의 인프라 + 부채 정리 단계.** 진입점 작업은 Part 1부터 시작.

---

## §0 환경 점검

### 작업

1. **Slice 10 종결 상태 검증**

   ```bash
   git checkout slice10
   pytest portfolio/tests -q  # 회귀 512 confirm
   ```

2. **브랜치 분기**

   ```bash
   git checkout -b slice11
   ```

3. **pre-commit hook 화이트리스트**

   ```bash
   grep "slice11" .git/hooks/pre-commit
   # 없으면 slice10 패턴 따라 추가
   ```

4. **Slice 10 자산 검증**
   - `docs/portfolio/coach/all_llm_calls.jsonl` 존재 + 200 entries
   - `portfolio/measure/estimator_v3.py` 존재 + `estimate_input_tokens()` 동작

### KPI

- 회귀 baseline 512 confirm
- Slice 10 자산 정상

---

## §1 #51 output_tokens estimator 본격 구현

### 배경

Slice 10에서 v3 인터페이스 분리 후 `estimate_output_tokens()`는 v2 char ratio 유지(이연). Slice 11 Step 0에서 본격 구현.

### 작업

1. **`portfolio/measure/estimator_v3.py` 갱신**
   - `estimate_output_tokens()` 본격 구현
   - 데이터 소스: `all_llm_calls.jsonl` (200 entries, output_tokens 실측 보유)
   - fitting 모델: **진입점별 char ratio** (e1~e6 별도 계수)
     - char ratio = output_tokens / output_chars
     - 진입점 식별: `source_file` 필드 기반 (slice별 prompt 구조 매핑)
   - fallback: 진입점 미식별 시 전체 평균 char ratio

   핵심 인터페이스:

   ```python
   def estimate_output_tokens(
       expected_output_chars: int,
       entry_point: str | None = None,  # "e1" | "e2" | ... | "e6"
       model: str = "claude-haiku-4-5-20251001",
   ) -> int:
       """진입점별 char ratio fitting 기반 output 추정."""
       ratio = _ENTRY_POINT_RATIOS.get(entry_point, _GLOBAL_RATIO)
       return int(expected_output_chars * ratio)
   ```

   ⚠️ **주의 (Slice 10 #52 Fallback A 영향)**: messages 원본이 없으면 진입점 식별이 불완전할 수 있음. `source_file` 파일명 패턴(`step8_2way_e3_raw.json` → e3)으로 매핑.

2. **`scripts/coach/backtest_output_estimator.py` 신규**
   - 입력: `all_llm_calls.jsonl`
   - 검증: 진입점별 `estimate_output_tokens()` vs 실측 output_tokens
   - **KPI 임계**: max_delta ≤ 10% (input ±2% 대비 완화 — output 변동성 본질적 ↑)
   - 산출물: `docs/portfolio/coach/slice11/output_backtest_report.md`

3. **단위 테스트** (`tests/coach/test_estimator_v3.py` 갱신)
   - 진입점별 추정 PASS (e1~e6)
   - fallback 동작 (미식별 진입점)
   - backward-compat (legacy `estimate_tokens()` 호출자 영향 0)
   - 5~7건

### 산출물

- `portfolio/measure/estimator_v3.py` (갱신)
- `scripts/coach/backtest_output_estimator.py`
- `docs/portfolio/coach/slice11/output_backtest_report.md`
- `tests/coach/test_estimator_v3.py` (갱신, +5~7건)

### KPI

- max_delta ≤ 10% (Slice 10 input ±2% 대비 완화)
- 진입점별 ratio 산출 6개 (e1~e6)
- backward-compat 100%

---

## §2 #52 raw messages 보존 정책

### 배경

Slice 10 §3 backtest가 raw messages 부재로 Fallback A 발동. Slice 11+ LLM 호출 시 messages 원본을 자동 dump하면 향후 estimator/cost 모델 fitting 데이터 자동 누적.

### 작업

1. **LLMClient wrapper hook 추가** (`portfolio/measure/llm_client.py` 또는 기존 위치)
   - 모든 LLM 호출 시 `messages + system + model + timestamp + cost_usd` JSONL 저장
   - 저장 위치: `docs/portfolio/coach/slice<N>/llm_messages.jsonl` (slice별 격리, 영구 보관)
   - 멱등성: 동일 호출 hash → 1회만 저장 (재실행 안전)
   - 환경 변수 toggle: `STOCKVIS_LLM_MESSAGE_DUMP=0` 시 비활성화 (테스트용)

   핵심 hook 패턴:

   ```python
   def _dump_messages(messages, system, model, response, slice_n):
       if os.getenv("STOCKVIS_LLM_MESSAGE_DUMP", "1") == "0":
           return
       record = {
           "messages": messages,
           "system": system,
           "model": model,
           "input_tokens": response.usage.input_tokens,
           "output_tokens": response.usage.output_tokens,
           "cost_usd": _compute_cost(response, model),
           "timestamp": datetime.utcnow().isoformat(),
           "hash": _hash_call(messages, system, model),
       }
       _append_jsonl(f"docs/portfolio/coach/slice{slice_n}/llm_messages.jsonl", record, dedupe_key="hash")
   ```

2. **`docs/portfolio/coach/MESSAGES_PERSISTENCE_POLICY.md` 신설**
   - 보존 정책 명문화 (위치, 멱등성, toggle, 보안 — 민감정보 포함 시 redact)
   - all_llm_calls.jsonl과의 관계 (messages는 별도 파일, slice별 격리)
   - Slice 12+ Step 0에서 통합 dump 시 사용법

3. **단위 테스트** (`tests/coach/test_messages_persistence.py` 신규)
   - hook 동작 PASS
   - 멱등성 (동일 hash 1회만 저장)
   - toggle off 시 호출 0
   - 5~7건

### 산출물

- `portfolio/measure/llm_client.py` 또는 wrapper 위치 (갱신)
- `tests/coach/test_messages_persistence.py`
- `docs/portfolio/coach/MESSAGES_PERSISTENCE_POLICY.md`

### KPI

- hook 멱등성 PASS
- toggle off 동작 PASS
- 보안 정책 명시 (redact 룰)

---

## §3 E6 mock fixture 추가 (A2 전용)

### 배경

A2는 1 portfolio × E1~E6 통합. 기존 GARP portfolio(Slice 1, 4)와 별개의 신규 portfolio 1건 필요(외삽 검증).

### 작업

1. **신규 portfolio 1건 정의**
   - 종목 5개 선정 (다양성 확보: 1 ETF + 4 stocks 권장)
   - preset: 신규 케이스 검증 위해 income 또는 dividend preset 선호 (기존 GARP/focused와 차별)
   - 기존 fixture 디렉토리 패턴 따름: `portfolio/tests/fixtures/coach/portfolio_a2.json` 또는 `.py`

2. **E6 분석엔진 mock 결과 작성** (`portfolio/tests/fixtures/coach/portfolio_a2_e6_analysis.json`)
   - Slice 4 E6 fixture 스키마 그대로 활용
   - 분석엔진 실제 호출 안 함 (D-4 a 채택: mock 일관)
   - 합리적인 mock 값 (Phase 2 #12 진입 전까지 manual 보정 인정)

3. **단위 테스트** (`tests/coach/test_portfolio_a2_fixture.py` 또는 기존에 추가)
   - schema validation PASS
   - 5 종목 × 분석 결과 1:1 매칭
   - 3~5건

### 산출물

- `portfolio/tests/fixtures/coach/portfolio_a2.json` (또는 .py)
- `portfolio/tests/fixtures/coach/portfolio_a2_e6_analysis.json`
- 단위 테스트 3~5건

### KPI

- fixture schema validation PASS
- 종목 5건 + 분석 결과 5건 매칭
- 기존 GARP/focused와 preset 차별성 확보

---

## §4 COST_POLICY.md 임계 상향 ($3.00 → $4.00)

### 작업

1. **`docs/portfolio/coach/COST_POLICY.md` 갱신**
   - 누적 임계: `$3.00 → $4.00`
   - CostGuard 80% 경고: `$2.40 → $3.20`
   - Slice 12+ 재상향 트리거: `$3.40` 사전 명시 (비용 패턴 일관)
   - 비용 패턴 명문화: `$1.00 → $1.50 → $2.00 → $3.00 → $4.00` (Slice 별 누적)
   - cap 정책 유지 명시: `mini-slice: $0.50 / full-slice: $1.00`

2. **`portfolio/measure/cost_guard.py` 갱신**
   - 누적 임계 + 80% 경고 임계 상수 갱신
   - 단위 테스트 갱신: 새 임계 위반 동작 검증
   - 3~5건 갱신

### 산출물

- `docs/portfolio/coach/COST_POLICY.md` (갱신)
- `portfolio/measure/cost_guard.py` (갱신)
- 단위 테스트 갱신 (3~5건)

### KPI

- `grep "\$4.00" COST_POLICY.md` PASS
- `grep "\$3.20" COST_POLICY.md` PASS (80% 경고)
- `grep "\$3.40" COST_POLICY.md` PASS (재상향 트리거)
- CostGuard $4.00 위반 차단 동작 PASS
- CostGuard $3.20 경고 발동 동작 PASS

---

## §5 KPI 9c 등록 (#48 v3 첫 실측 검증)

### 작업

1. **`docs/portfolio/coach/slice11/kpi_step0.md`에 KPI 9c 정의 사전 등록**
   - 발동 시점: Slice 11 Part 3 smoke 첫 LLM 호출
   - 룰: `count_tokens(messages, system, model)` 사전 호출 → 실제 `messages.create()` 호출 후 `response.usage.input_tokens` 대조
   - 임계: `|estimated - actual| / actual × 100 ≤ 2%`
   - FAIL 시 #48 재오픈

2. **smoke 테스트 룰 사전 작성** (Part 3에서 실제 발동)
   - `tests/coach/test_kpi_9c_estimator_validation.py` 스켈레톤 작성 (Part 3에서 실측 채우기)

### 산출물

- `docs/portfolio/coach/slice11/kpi_step0.md` 일부 (KPI 9c 정의)
- `tests/coach/test_kpi_9c_estimator_validation.py` (스켈레톤만)

### KPI

- KPI 9c 정의 명문화
- 스켈레톤 테스트 파일 존재 (Part 3 발동 대기)

---

## §6 회귀 분류 + Step 0 KPI 검증

### 작업

1. **`portfolio/tests/helpers/regression_classifier.py` 갱신**
   - `messages_persistence` 카테고리 추가 (테스트 분류)
   - `output_estimator` 카테고리 추가
   - 기존 `data-prep` 카테고리 (Slice 10) 재사용 검토

2. **Step 0 KPI 매트릭스 검증** (자동)
   - `pytest portfolio/tests -q` → 회귀 +13~18 확인
   - IDENTICAL hash 7/7 유지
   - 회귀 9a/9b 분류 PASS

### 산출물

- `portfolio/tests/helpers/regression_classifier.py` (갱신)
- `portfolio/tests/slice11/test_regression_classifier.py` (+2 룰)

### KPI

- 회귀 분류 정확도 100%
- IDENTICAL hash 7/7 PASS
- KPI 9a (cost ±30%) / 9b (no-cost ±50%) PASS

---

## §7 Step 0 종결 보고

### 작업

1. **`docs/portfolio/coach/slice11/step0_closing.md` 작성**
   - 회귀, IDENTICAL, 비용, LLM 호출
   - KPI 매트릭스 (11~12건)
   - **#51 close**: output estimator max_delta 검증 결과
   - **#52 정책 정착**: messages 보존 hook + MESSAGES_PERSISTENCE_POLICY.md
   - Slice 11 Part 1 진입 준비 상태 보고

2. **`docs/portfolio/coach/slice11/kpi_step0.md` 완성** (KPI 9c 정의 포함)

### 산출물

- `docs/portfolio/coach/slice11/step0_closing.md`
- `docs/portfolio/coach/slice11/kpi_step0.md`

---

## §8 KPI 매트릭스 (12건)

| #   | KPI                                              | 임계                | 측정                  |
| --- | ------------------------------------------------ | ------------------- | --------------------- |
| 1   | #51 output estimator max_delta                   | ≤ 10%               | backtest 결과         |
| 2   | 진입점별 char ratio 산출                         | 6개 (e1~e6)         | 진입점 매핑           |
| 3   | #52 messages 보존 hook 멱등성                    | PASS                | 단위 테스트           |
| 4   | #52 toggle off 동작                              | PASS                | 단위 테스트           |
| 5   | E6 mock fixture schema validation                | PASS                | 단위 테스트           |
| 6   | COST_POLICY $4.00 / $3.20 / $3.40 명시           | PASS                | grep                  |
| 7   | CostGuard $4.00 위반 차단 + $3.20 경고           | PASS                | 단위 테스트           |
| 8   | KPI 9c 정의 명문화                               | PASS                | 파일 존재             |
| 9   | IDENTICAL hash 유지                              | 7/7                 | test_static_integrity |
| 10  | backward-compat (estimator v3 input + v2 호출자) | 100%                | 기존 테스트           |
| 11  | 회귀 +13~18 (Step 0 단독 mini-slice 수준)        | predicted ±30%/±50% | classifier            |
| 12  | 누적 비용                                        | ≤ $2.43             | CostGuard             |

---

## §9 Fallback 룰

| 트리거                             | 조치                                                                                        |
| ---------------------------------- | ------------------------------------------------------------------------------------------- |
| §1 backtest max_delta > 10%        | 진입점별 fitting을 multivariate로 확장(작업 시간 +1h), 또는 임계 완화 ≤ 15% + #51 keep_open |
| §2 messages dump storage 충돌      | dedupe_key 변경 (`hash` → `hash+timestamp`), 재실행                                         |
| §3 E6 mock 작성 시간 ≥ 1h          | preset을 GARP 변형으로 단순화 (전혀 새 preset 대신)                                         |
| §4 CostGuard 변경으로 회귀 +5 초과 | cost_guard.py 테스트 분리 (data-prep 카테고리)                                              |
| 회귀 +18 초과                      | mini-slice 한계 위반 — 사용자 보고 + Part 1 분리 검토                                       |
| 누적 비용 $2.45 초과               | Step 0 LLM 호출 차단, 사용자 보고                                                           |

---

## §10 작업 순서 (recommend)

| §   | 작업                                            | 예상 시간 | 누적 |
| --- | ----------------------------------------------- | --------- | ---- |
| §0  | 환경 점검                                       | 15분      | 0:15 |
| §1  | #51 output estimator + backtest + 테스트        | 1.5h      | 1:45 |
| §2  | #52 messages 보존 hook + 정책 문서 + 테스트     | 1.0h      | 2:45 |
| §3  | E6 mock fixture (portfolio + analysis + 테스트) | 45분      | 3:30 |
| §4  | COST_POLICY 갱신 + CostGuard 갱신               | 30분      | 4:00 |
| §5  | KPI 9c 등록 + 스켈레톤                          | 15분      | 4:15 |
| §6  | 회귀 분류 + KPI 검증                            | 30분      | 4:45 |
| §7  | 종결 보고                                       | 15분      | 5:00 |

**총 ~5시간** (Slice 10 동일 수준, 1세션 적정)

---

## §11 산출물 체크리스트 (13건)

### 신규 (9건)

- [ ] `scripts/coach/backtest_output_estimator.py`
- [ ] `docs/portfolio/coach/slice11/output_backtest_report.md`
- [ ] `tests/coach/test_messages_persistence.py`
- [ ] `docs/portfolio/coach/MESSAGES_PERSISTENCE_POLICY.md`
- [ ] `portfolio/tests/fixtures/coach/portfolio_a2.json` (또는 .py)
- [ ] `portfolio/tests/fixtures/coach/portfolio_a2_e6_analysis.json`
- [ ] `tests/coach/test_kpi_9c_estimator_validation.py` (스켈레톤)
- [ ] `docs/portfolio/coach/slice11/kpi_step0.md`
- [ ] `docs/portfolio/coach/slice11/step0_closing.md`

### 갱신 (4건)

- [ ] `portfolio/measure/estimator_v3.py` (output estimator 본격 구현)
- [ ] `tests/coach/test_estimator_v3.py` (+5~7건)
- [ ] `portfolio/measure/llm_client.py` (또는 wrapper, messages hook)
- [ ] `docs/portfolio/coach/COST_POLICY.md` ($4.00/$3.20/$3.40)
- [ ] `portfolio/measure/cost_guard.py` (임계 상수 갱신)
- [ ] `portfolio/tests/helpers/regression_classifier.py` (+2 카테고리)
- [ ] `portfolio/tests/slice11/test_regression_classifier.py` (+2 룰)
- [ ] `.git/hooks/pre-commit` (slice11 화이트리스트)

---

## §12 회신 형식 (Claude Code → 사용자)

```
Slice 11 Step 0 종결 (trio 5-Part 시작).
- 회귀: 512 → ___ (+___)
- IDENTICAL: ___/7
- 비용 단독: $___ / 누적: $___ (마진 ___%)
- LLM 호출: ___/50
- KPI 12/12: ___ PASS, ___ FAIL
- #51 close: max_delta ___% (목표 ≤10%)
- #52 정책 정착: PASS / FAIL
- E6 mock fixture: PASS / FAIL
- 임계 상향: $3.00 → $4.00 갱신 PASS

Slice 11 Part 1 진입 준비 상태: ___
KPI 9c 스켈레톤: 등록 완료, Part 3 발동 대기

git log --oneline slice10..HEAD
[commit hashes]
```

manual 검증 필요 사항이 있으면 별도 섹션으로 명시.
