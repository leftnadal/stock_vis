# Slice 6 Part 2 v2 — 작업 지시서

> **버전**: v2 (Part 1 완료 보고 검증 후 명시적 분리 구성)
> **시점**: Slice 6 Part 1 종결 / Part 2 미실행
> **브랜치**: `portfolio`
> **누적 회귀**: 372 / 누적 광의 비용: $0.764
> **대상 진입점**: concentrated_portfolio E3 portfolio-level
> **선결 처리**: Part 1 유의사항 #1 (외삽 검증) + #3 (token_budgets 등록) + #4 (prompt builder 보강)

---

## 0. 컨텍스트 및 v2 구성 근거

Part 1 종결 시 prompt builder가 placeholder만 채우는 minimal 상태(input 평균 761)였고, Slice 5 e3 수준(input P90 4,359)에 도달하려면 5~6배 보강이 필요. mock test와 prompt 보강을 혼재시키면 재작업 위험 30~40%로 분석되어 **Part 2 = Step A(prompt 보강) → Step B(mock/fixture) 명시적 분리** 채택.

**v2 구성 핵심**:

- **Step A** = prompt builder 보강 + token 재측정 + estimator 외삽 재검증 + `token_budgets["e3_portfolio"]` 정식 등록
- **Step B** = mock LLM response fixture + 서비스 흐름 단위 테스트 (Slice 4·5 패턴 mirror)

**진행 순서**: Step A → Step B (sequential, Step B의 mock fixture가 Step A의 최종 prompt에 의존)

**선결 처리 매핑**:

- 유의 #1 (estimator 외삽 능력 미검증) → Step A에서 보강된 prompt로 estimator 재실행 → 추정 vs 실측 ±20% 이내 검증
- 유의 #3 (`token_budgets["e3_portfolio"]` 미등록) → Step A 종료 시 정식 등록
- 유의 #4 (prompt builder minimal) → Step A 1.1~1.4

---

## 1. Step A — Prompt Builder 보강 + Token 재측정 + Budget 등록

### 1.1 목적

현 minimal builder(input 평균 761)를 Slice 5 e3 수준(input 4,000~6,000)으로 보강. 보강된 prompt 기준으로 estimator 외삽 능력 검증(#β2 후속) + `token_budgets["e3_portfolio"]` 정식 등록.

### 1.2 산출물

1. `portfolio/prompts/e3_portfolio/builder.py` 확장 (system prompt + AnalysisContext JSON dump + few-shot 4)
2. `portfolio/prompts/e3_portfolio/system_prompt.txt` 신규 (또는 builder.py 내 상수)
3. `portfolio/prompts/e3_portfolio/few_shots/` 4개 example (concentrated_balanced / concentrated_misfit / concentrated_factor / concentrated_income)
4. `token_budgets.py` `BUDGETS["e3_portfolio"]` 정식 등록
5. `portfolio/llm/budget_estimator.py` 외삽 재검증 함수 추가 (또는 기존 backtest 확장)
6. 회귀 테스트 +3~5
7. `docs/portfolio/coach/slice6/step_a_prompt_reinforcement.md` 결정 보존

### 1.3 Prompt builder 보강 구성

**현재 구조 (minimal, Part 1)**:

- 7 placeholder만 치환 → input 평균 761

**보강 후 구조 (Slice 5 e3 mirror)**:

| 구성요소                       | 추정 input 토큰 | 비고                                                            |
| ------------------------------ | --------------- | --------------------------------------------------------------- |
| system prompt                  | 800~1,200       | portfolio-level 평가자 역할 + 출력 schema 준수 지시             |
| schema 명세 (JSON schema dump) | 400~600         | 6 필드 + Literal enum + 길이 제약                               |
| AnalysisContext JSON dump      | 1,500~2,500     | preset 메타 + holdings 5~10 + Core 7종 + 분석엔진 산출값        |
| few-shot 4 examples            | 1,200~1,600     | concentrated_balanced/misfit/factor/income (V1·V2·V3·V5 mirror) |
| 변수 슬롯 치환부               | 100~200         | 기존 placeholder 부분                                           |
| **합계**                       | **4,000~6,100** | **목표 도달**                                                   |

### 1.4 Few-shot examples 4종

| Example               | 기반 fixture | 카테고리      | 의도                     |
| --------------------- | ------------ | ------------- | ------------------------ |
| concentrated_balanced | V1 mirror    | growth        | preset aligned 패턴 학습 |
| concentrated_misfit   | V2 mirror    | growth misfit | misaligned 패턴 학습     |
| concentrated_factor   | V3 mirror    | factor        | 다중 sector 집중 패턴    |
| concentrated_income   | V5 mirror    | income        | dividend-tilted 패턴     |

→ V4 (value)는 few-shot에서 제외(test set 다양성 확보용). 5 카테고리 cover는 학습/평가 모두에서 보장.

### 1.5 Token 재측정 + Estimator 외삽 검증

**측정 절차**:

1. 보강된 builder로 V1~V5 fixture 각각 prompt 생성
2. anthropic `count_tokens` API로 실측 input 토큰 측정
3. V1~V5 평균 input + output 추정(660 ×1.5 = 1,000) → total → ×1.5 buffer
4. `estimate_budget_for_entrypoint("e3_portfolio", sample_prompts=[V1~V5])` 실행
5. **추정 vs 실측 편차 ±20% 이내 검증** (외삽 재검증 KPI)

**budget 등록**:

- 실측 input P90(V1~V5 max) + output 1,000 → ×1.5 → round-up 500
- 예: input 5,200 max + output 1,000 = 6,200 → ×1.5 = 9,300 → round-up = **9,500** (잠정값과 일치 시 #β2 close 완전 검증)

### 1.6 회귀 테스트 (+3~5)

```
test_e3_portfolio_prompt_input_tokens_4k_to_6k
test_e3_portfolio_few_shots_4_examples_loadable
test_estimate_budget_e3_portfolio_extrapolation_within_20pct
test_token_budgets_e3_portfolio_registered
test_e3_portfolio_builder_system_prompt_included (자연 흡수 후보)
```

### 1.7 Acceptance Criteria

| 항목                             | 기준                                                       |
| -------------------------------- | ---------------------------------------------------------- |
| prompt input 토큰                | V1~V5 평균 4,000~6,000 도달                                |
| few-shot 4종 로딩                | 4 examples 모두 valid (schema parse + min/max length 제약) |
| **estimator 외삽 검증**          | **추정 vs 실측 ±20% 이내 (#β2 후속 verification)**         |
| token_budgets 등록               | `BUDGETS["e3_portfolio"]` 정식 값 등록 (round-up 500)      |
| 잠정 9,500/10,000 reconciliation | 실측 등록값과 ±30% 이내 (>30% 시 분기 F3)                  |
| 회귀                             | +3~5 PASS, 기존 372 영향 0건                               |
| 비용                             | $0 (count_tokens API + 정적 분석)                          |
| 시간                             | 40~60분                                                    |

---

## 2. Step B — Mock LLM Response Fixture + 서비스 흐름 단위 테스트

### 2.1 목적

Step A 보강된 prompt 기준으로 LLM 응답 mock fixture 작성 + service layer 흐름 단위 검증. Part 3(real LLM 매트릭스 15 cases) 진입 전 정적 검증 완료.

### 2.2 산출물

1. `portfolio/tests/fixtures/mock_responses/e3_portfolio/` 디렉토리
   - `v1_haiku.json`, `v1_sonnet.json`, ..., `v5_haiku.json`, `v5_sonnet.json` (10건)
2. `portfolio/services/e3_portfolio_service.py` 서비스 layer (또는 기존 e3 service 확장)
3. `portfolio/tests/test_e3_portfolio_service.py` 서비스 단위 테스트
4. 회귀 테스트 +10~15
5. `docs/portfolio/coach/slice6/step_b_mock_fixtures.md` 결정 보존

### 2.3 Mock fixture 구성

| V × 모델    | 파일           | 의도                                   |
| ----------- | -------------- | -------------------------------------- |
| V1 × haiku  | v1_haiku.json  | growth aligned, haiku 글쓰기 (primary) |
| V1 × sonnet | v1_sonnet.json | growth aligned, sonnet fallback 후보   |
| V2 × haiku  | v2_haiku.json  | growth misaligned                      |
| V2 × sonnet | v2_sonnet.json | growth misaligned                      |
| V3 × haiku  | v3_haiku.json  | factor                                 |
| V3 × sonnet | v3_sonnet.json | factor                                 |
| V4 × haiku  | v4_haiku.json  | value                                  |
| V4 × sonnet | v4_sonnet.json | value                                  |
| V5 × haiku  | v5_haiku.json  | income                                 |
| V5 × sonnet | v5_sonnet.json | income                                 |

→ **gemini 제외** (Slice 1 9/9 폴백 후 매트릭스 일관 제외 정책 유지)
→ mock 응답은 E3PortfolioCommentary schema 준수, 6 필드 모두 포함, preset_alignment Literal 값 정확

### 2.4 Mock 응답 작성 가이드

각 mock은 **현실적 LLM 응답을 재현**해야 함:

- haiku: 글쓰기 가설 5/5 정착 → 풍부한 어휘, naturalness 높음 (목표 3.5+)
- sonnet: 단순 명료, focus 강함 (Slice 5 preset 다양성 민감 특성 반영)
- 6 필드 모두 length 제약 준수 (holistic 30~300, 나머지 20~200)
- preset_alignment: V1·V4·V5 = aligned, V2 = misaligned, V3 = partial
- confidence: V1~V5 모두 3~5 (LLM 자신도 보통 이상)

### 2.5 서비스 layer 흐름

```
Input: AnalysisContext (concentrated_portfolio + preset)
   ↓
1. build_e3_portfolio_prompt(context) → prompt string (Step A 보강본)
   ↓
2. llm_client.invoke(prompt, model) → raw response
   ↓
3. parse_e3_portfolio_response(raw) → E3PortfolioCommentary
   ↓
4. validate() + cost tracking (CostGuard)
   ↓
Output: E3PortfolioCommentary + metadata
```

Mock 단계에서는 2번을 mock fixture로 치환.

### 2.6 회귀 테스트 (+10~15)

```
test_e3_portfolio_service_v1_haiku_mock_flow
test_e3_portfolio_service_v1_sonnet_mock_flow
... (V1~V5 × haiku/sonnet 10건 parametrize)
test_e3_portfolio_service_invalid_mock_raises_validation_error
test_e3_portfolio_service_preset_alignment_enum_strict
test_e3_portfolio_service_cost_guard_integration
```

### 2.7 Acceptance Criteria

| 항목              | 기준                                                                |
| ----------------- | ------------------------------------------------------------------- |
| Mock fixture 10건 | V1~V5 × haiku/sonnet 모두 schema parse PASS                         |
| 서비스 흐름       | build → invoke(mock) → parse → validate 4단계 PASS                  |
| preset_alignment  | Literal Enum 5/5 정합 (V1/V4/V5=aligned, V2=misaligned, V3=partial) |
| CostGuard 통합    | mock 단계에서도 reset_for_slice 멱등 동작 PASS                      |
| 회귀              | +10~15 PASS, 기존 375~377(Step A 후) 영향 0건                       |
| 비용              | $0 (mock이라 LLM 호출 0)                                            |
| 시간              | 60~90분                                                             |

---

## 3. 분기 시나리오 처리 절차

### F1 — Step A prompt 보강 후 input < 3,000

- 원인: system prompt 또는 few-shot 분량 부족, AnalysisContext JSON dump 미포함
- 처리: system prompt 확장 (역할 설명 + 출력 schema 명세 보강), few-shot 길이 확대, AnalysisContext 전체 dump 포함 검증
- 보정 사이클: Step A 안에서 1회 재측정 (별도 step 분리 불요)

### F2 — Estimator 외삽 검증 ±20% 초과

- 원인: estimator가 보강된 prompt 구조 학습 못 함 (system + few-shot 가중치 미반영)
- 처리: estimator에 prompt-specific 가중치 도입 (system token, few-shot token 별도 추정)
- **#β2 재오픈** (PS 2.0 추가 작업 예상)
- 후속: Slice 6 Step 9 슬롯 후보 갱신 (현재 #19 PS 2.0 vs #β2 재오픈 PS 2.0 → 비교 결정)

### F3 — token_budgets 등록값 vs 잠정 9,500/10,000 편차 >30%

- 원인: Part 1 잠정 baseline이 실측과 큰 괴리 (output 추정 660 vs 실측 차이)
- 처리: `BUDGETS["e3_portfolio"]` 실측 기준 등록 (잠정 폐기), Part 1 결정 보존 docs에 사후 정정 노트 추가
- 신규 부채 등재 검토 (PS 1.0~1.5)

### F4 — Mock fixture schema validation FAIL

- 원인: mock 작성 시 length 제약 위반 또는 Literal enum 미정합
- 처리: 해당 mock fixture 즉시 수정 (schema 변경 아님 — schema는 Part 1 확정)
- Step 1.5 사이클 불필요 (mock만 수정)

---

## 4. Part 2 종합 KPI

| 항목             | 목표                                                                |
| ---------------- | ------------------------------------------------------------------- |
| 회귀 누적        | 372 → 385~395 (+13~20)                                              |
| 비용 단독        | $0 (정적 분석 + count_tokens API + mock)                            |
| 누적 광의        | $0.764 → $0.764 (불변)                                              |
| 신규 부채        | 0건 예상 (F2 발동 시 #β2 재오픈 PS 2.0, F3 발동 시 신규 PS 1.0~1.5) |
| 시간             | 1.5~2.5시간 (Step A 40~60분 + Step B 60~90분)                       |
| **유의 #1 처리** | estimator 외삽 검증 ±20% 이내 PASS                                  |
| **유의 #3 처리** | `BUDGETS["e3_portfolio"]` 정식 등록                                 |
| **유의 #4 처리** | prompt input 4,000~6,000 도달                                       |

---

## 5. 회수 양식 (Step A/B 실행 후)

```
[Slice 6 Part 2 완료 보고]

== Step A ==
A1. Prompt 보강 후 input 토큰:
  V1: ___ tokens
  V2: ___ tokens
  V3: ___ tokens
  V4: ___ tokens
  V5: ___ tokens
  평균: ___ / max: ___
  → 목표 4,000~6,000 도달 여부: Y / N (N 시 F1 분기)

A2. Few-shot 4 examples 로딩:
  concentrated_balanced (V1 mirror): PASS / FAIL
  concentrated_misfit (V2 mirror):    PASS / FAIL
  concentrated_factor (V3 mirror):    PASS / FAIL
  concentrated_income (V5 mirror):    PASS / FAIL

A3. Estimator 외삽 검증:
  추정 input=___, output=___, total=___, with_buffer=___
  실측 input(P90 V1~V5)=___, output=___, total=___
  편차 ±__%
  → ±20% 이내: Y / N (N 시 F2 분기 + #β2 재오픈)

A4. token_budgets["e3_portfolio"] 등록값:
  계산: input ___ + output ___ = ___, ×1.5 = ___, round-up 500 = ___
  잠정 9,500/10,000 대비 편차 ±__%
  → ±30% 이내: Y / N (N 시 F3 분기)

A5. 회귀 신규 +___개 (목표 +3~5)

A6. 신규 부채: ___ (또는 "0건")

== Step B ==
B1. Mock fixture 10건 schema parse:
  V1 × haiku: PASS / FAIL  | V1 × sonnet: PASS / FAIL
  V2 × haiku: PASS / FAIL  | V2 × sonnet: PASS / FAIL
  V3 × haiku: PASS / FAIL  | V3 × sonnet: PASS / FAIL
  V4 × haiku: PASS / FAIL  | V4 × sonnet: PASS / FAIL
  V5 × haiku: PASS / FAIL  | V5 × sonnet: PASS / FAIL
  → FAIL 발생 시 F4 분기 (mock만 수정)

B2. 서비스 흐름 4단계:
  build_prompt:    PASS / FAIL
  invoke (mock):   PASS / FAIL
  parse:           PASS / FAIL
  validate:        PASS / FAIL

B3. preset_alignment Enum 정합:
  V1=aligned / V2=misaligned / V3=partial / V4=aligned / V5=aligned
  → 5/5 정합: Y / N

B4. CostGuard 통합:
  reset_for_slice 멱등: PASS / FAIL
  mock 비용 카운팅: $0 / $___

B5. 회귀 신규 +___개 (목표 +10~15)

== 종합 ==
- 누적 회귀: 372 → ___
- Part 2 단독 비용: $___
- 누적 광의: $0.764 → $___
- 기존 372 영향: ___건
- Part 2 소요 시간: Step A ___분 / Step B ___분
- 분기 시나리오 발동: F1 / F2 / F3 / F4 / 없음
- 유의 #1 처리: PASS / 재오픈
- 유의 #3 처리: 등록값 ___
- 유의 #4 처리: input ___ tokens (목표 4k~6k)
```

---

## 6. 작업 흐름 (Claude Code용)

1. **Step A 실행** (sequential)
   - builder.py 보강: system prompt + AnalysisContext JSON dump + few-shot 4
   - V1~V5 prompt input 토큰 측정 (count_tokens API)
   - estimator로 e3_portfolio 추정 → 실측과 편차 검증
   - `BUDGETS["e3_portfolio"]` 등록
   - 회귀 +3~5 추가
   - **검증 통과 → Step B / 실패 시 분기 F1·F2·F3 처리 후 Step B**

2. **Step B 실행** (Step A 통과 후)
   - mock fixture 10건 작성 (V1~V5 × haiku/sonnet)
   - 서비스 layer (또는 e3 서비스 확장)
   - 단위 테스트 작성 + parametrize 10건
   - 회귀 +10~15 추가
   - **schema parse PASS → 통과, FAIL 시 F4 분기 (mock 수정)**

3. **결과 회수**
   - 위 5번 양식 그대로 채워서 보고
   - 분기 시나리오 발동 여부 명시
   - 유의 #1·#3·#4 처리 결과 명시

4. **commit 메시지 권장**
   - `feat(slice6/part2/stepA): reinforce e3_portfolio prompt builder + register budget`
   - `feat(slice6/part2/stepB): add e3_portfolio mock fixtures + service flow tests`

---

## 7. Part 3 진입 전 체크포인트

Part 2 종결 후 Part 3(real LLM 매트릭스 15 cases) 진입 전 확인:

- [ ] `BUDGETS["e3_portfolio"]` 정식 등록 완료
- [ ] estimator 외삽 검증 PASS (또는 #β2 재오픈 처리 완료)
- [ ] V1~V5 fixture × haiku/sonnet mock 10건 정합 PASS
- [ ] 서비스 layer 흐름 4단계 단위 테스트 PASS
- [ ] CostGuard 통합 검증 PASS
- [ ] 신규 부채 0건 또는 처리 계획 명시
- [ ] Slice 1 e1 + Slice 3 e2 IDENTICAL hash KPI 유지

Part 3 = real LLM 15 cases (V1~V5 × haiku/sonnet/gemini 또는 haiku/sonnet 10건), 비용 추정 $0.10~0.20.
