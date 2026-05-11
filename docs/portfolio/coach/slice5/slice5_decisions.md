# slice5_decisions.md — Slice 5 종결 결정 기록 (자동 단계 종결 시점)

> 작성일: 2026-05-07
> Slice 5 자동 단계 종결 시점 결정 기록 보존. winner / 글쓰기 가설 외삽 / Slice 6 진입점 1순위는 manual eval 후 1턴에 일괄 충전.

---

## §1. Slice 5 누적 결정 표 (Part 1 + Part 2 통합)

13건 결정 (Part 1 6건 + Part 2 7건):

| 일자 | 결정 | 채택 | 가중합 |
|---|---|---|---|
| 2026-05-07 (Part 1) | Q1+N3 매트릭스 | hybrid 7 (GARP3 재활용 + 4 preset focused, 5 카테고리) | 4.40 |
| 2026-05-07 (Part 1) | Q5 Step 9 슬롯 (1차) | #11 일반화 (`format_metrics_to_str`) | 4.80 |
| 2026-05-07 (Part 1) | N1 (system, user) tuple | service concat + 백로그 #19 등록 | 4.55 |
| 2026-05-07 (Part 1) | Q3 평가 차원 | naturalness + insight + completeness | 4.65 |
| 2026-05-07 (Part 1) | Q6 #γ1 처리 | 광의 단일 정책 + COST_POLICY.md 신설 | 5.00 |
| 2026-05-07 (Part 1) | Q4-N2 preset | 11 preset (concentrated 제외) + 백로그 #20 | 단순 확인 |
| 2026-05-07 (Part 2) | Q5 Step 9 작업 형태 | A: 통합 + E2/E3 모두 변경 + deprecated wrapper | 4.40 |
| 2026-05-07 (Part 2) | Q1 Step 6 fixture | e3_baseline_garp_tech | 단순 확인 |
| 2026-05-07 (Part 2) | Q2 latency 임계 | 16,000ms (Slice 4 #9 mirror) | 단순 확인 |
| 2026-05-07 (Part 2) | Q3 budget 추정 | 1500 유지 (실측 후 7000으로 갱신) | 단순 확인 |
| 2026-05-07 (Part 2) | Q4 Step 8 매트릭스 | hybrid 7 그대로 | 단순 확인 |
| 2026-05-07 (Part 2) | N1 환경 차이 3건 추가 | 자동 변환 적용 (8건 통합 명시) | 단순 확인 |
| 2026-05-07 (Part 2) | N2 Slice 4 보고서 광의 갱신 | 변경 없음 | 단순 확인 |

종결 분석 시점 결정 (2건, 본 산출 직전):
| 결정 | 채택 | 가중합 |
|---|---|---|
| 4개 산출물 작성 시점 | C: 분리 작성 (winner 독립부 즉시 + 의존부 manual eval 후) | 4.30 |
| #β2 처리 방식 | A: 백로그 등록 + Slice 6 Step 0 후보 | 4.50 |

---

## 부록 A — Slice 5 종결 결정 표 (자동 단계 종결 시점 갱신)

| 항목 | 값 (Part 1 시점) | 값 (Part 2 자동 단계 종결 시) | manual eval 후 갱신 예정 |
|---|---|---|---|
| 진입점 | E3 (지표 코멘트, preset 외삽 검증) | (동일) | — |
| Default provider | haiku (글쓰기 가설 4/4 정착 외삽) | (실측 검증 진행 — Step 8 자동 부분 PASS) | **Step 8 winner로 검증** |
| Fixture 전략 | hybrid 7 (GARP 3 재활용 + 4 preset focused) | (동일) | — |
| 5 preset 선정 | garp / buffett / dividend_growth / quality_factor / contrarian | (동일) | — |
| 5 카테고리 cover | value / growth / income / factor / special | (동일) | — |
| 평가 차원 | naturalness + insight (manual) + completeness (자동) | (동일) | — |
| Step 6 fixture | e3_baseline_garp_tech | (적용 ✓, 4 판정 모두 PASS) | — |
| Step 6 임계 | cost $0.020 / latency 16,000ms | **실측: cost $0.00492 (24.6%) / latency 4,100ms (25.6%)** ✓ | — |
| Step 7 e3 budget | 1차 추정 1,500 | **실측 P90=4,359 → 7,000 등록 (+366% 편차)** | — |
| Step 7 #β1 처리 | 자연 검증 절차 명시 | **#β1 closed** (chars/3 평균 +2.9% 정상, 보정 미실시) | — |
| Step 7 #β2 신규 발견 | — | **#β2 등록 (PS 3.0)**: budget 1차 추정 모델 일반화. Slice 6 Step 0 후보 | — |
| Step 8 매트릭스 | 7 × 2 = 14 | **14 calls 종결, fallback 0** | — |
| Step 8 schema+completeness | (자동 검증) | **14/14 PASS** ✓ | — |
| **Step 8 winner** | (Part 2 종결 시 기재) | **[manual eval 대기]** | **haiku ✓** (efficiency 145% 우세) |
| **Step 8 lex pass rate** | (Part 2 종결 시 기재) | **[manual eval 대기]** | **haiku 6/7 (85.7%) / sonnet 7/7 (100%)** |
| **Step 8 efficiency 차이** | (Part 2 종결 시 기재) | **[manual eval 대기]** | **+145%** (≫ 5% 임계, mode=EFFICIENCY) |
| **글쓰기 가설 외삽 검증** | (Part 2 종결 시 기재) | **[manual eval 대기]** | **5/5 정착 ✓** (preset 외삽 위험 영구 해소) |
| Step 9 작업 | #11 일반화 (`format_metrics_to_str` + deprecated wrapper) | **완료 ✓** + 단위 테스트 +10 (예상 +3 대비 커버리지 증가) | — |
| Step 9 IDENTICAL hash | baseline 명시 | **Slice 1·3 모두 통과 ✓** (`917fa3ef…0f7b9` / `5594c6ab…f3ba`) | — |
| Step 0 #γ1 처리 | 광의 단일 정책 | **Part 1 완료 ✓**, Part 2 validation_report 광의 단일 정책 적용 ✓ | — |
| (system, user) tuple | service concat (백로그 #19 Slice 6+) | (동일) | — |
| concentrated_portfolio | 제외 (백로그 #20) | (동일) | — |
| 환경 차이 자동 변환 | 5건 (Part 1) → 8건 (Part 2) | 모두 적용 ✓ (`llm.py` 통합 / `PROVIDER_KWARGS` / `LLMResponse.metadata_dict()` 추가) | — |
| 케이스 A~G 발동 | — | **A·B·C·D·E·G 미발동, F는 manual eval 대기** | **A~G 0/7 미발동 ✓** (F 미발동, winner=haiku) |
| 누적 호출 (Slice 5 단독) | — | **15 / 50 (마진 35)** ✓ | (동일) |
| 누적 비용 (Slice 5 단독 광의) | — | **$0.179** ($0.20 임계 89.5%) | (동일) |
| 누적 비용 (Slice 1~5 광의) | $0.585 (진입 시) | **$0.764** | (동일) |
| **Slice 6 진입 결정** | Slice 5 종결 회고 시 | **부록 F.1 frame 작성** | **concentrated_portfolio E3 확정** (가중합 4.05 vs E4 3.40, 마진 +0.65) |

---

## 부록 B — Slice 5 백로그 통합 표 (자동 단계 종결 시점)

### B.1 Slice 4 11건의 Slice 5 처리 결과

| # | 항목 | PS | Slice 5 처리 결과 |
|---|---|---|---|
| 11 | metrics_table 일반화 | 1.5 | **Slice 5 Step 9 완료 ✓** (`format_metrics_to_str` + deprecated wrapper) |
| 5 | TOKEN_BUDGET LLMClient 통합 잔여 | 2.0 | Slice 6+ |
| 6 | Step 8 raw output CSV 옵션 | 1.0 | Slice 6+ |
| 7 | Mock LLMClient mode dict 매핑 | 1.0 | Slice 6+ |
| 8 | LLMClient entrypoint 인자 + 가드레일 | 2.5 | Slice 6+ Step 9 슬롯 후보 |
| 10 | E2 keyword_match 룰 보완 | 1.5 | Slice 6+ |
| 13 | run_step6_*.py 5종 latency 일괄 16,000ms | 1.0 | run_step6_e3_smoke.py 자연 흡수 1건 + 기존 5 파일 Slice 6+ |
| 14 | score_step8.py CLI 인자 확장 | 1.5 | Slice 6+ |
| 15 | E6 자동 평가 룰 정교화 | 1.5 | Slice 6+ (Slice 5 Step 8 미흡수) |
| 16 | E6 latency 24s 초과 sonnet 패턴 | 1.0 | Slice 6+ |
| 17 | auto_eval_e6.py 패턴 일반화 | 2.0 | Slice 6+ |

**처리율**: Slice 4 11건 중 Slice 5 완료 1건 (#11) + 자연 흡수 부분 1건 (#13).

### B.2 Slice 5 신규 백로그 (Part 1 + Part 2)

| # | 항목 | PS | 등록 시점 | 트리거 |
|---|---|---|---|---|
| 18 | score_step8_e5.py argparse --entrypoint 인자 | 1.0 | Slice 4 검증 | (이전 등록) |
| 19 | LLMClient.complete system 인자 추가 | 2.0 | Slice 5 Part 1 | E3 (system, user) tuple → service concat 임시 |
| 20 | concentrated_portfolio portfolio-level E3 별도 슬라이스 | 2.0 | Slice 5 Part 1 | 5 preset에서 concentrated 제외 |
| 21 | format_metrics_table deprecated wrapper 제거 | 0.5 | Slice 5 Part 2 | Step 9 후 호출처 통합 완료 |
| 22 | LLMResponse.metadata_dict() 표준 정착 검증 | 1.0 | Slice 5 Part 2 | 4 슬라이스 호출처 일관성 검증 |

### B.3 Slice 5 자동 단계 종결 발견 신규 부채 (2건)

| # | 항목 | PS | 사유 |
|---|---|---|---|
| **#β2** | budget 1차 추정 모델 일반화 (진입점별 prompt 구조 반영) | **3.0** | Step 7 +366% 편차 발견. e3 prompt = system + few-shot examples + JSON input 구조. 1차 추정이 출력 길이만 반영 → `estimate_budget_for_entrypoint()` 헬퍼 도입. **Slice 6 Step 0 후보** |
| #23 (후보) | 비용 임계 $0.20 → $0.25 상향 검토 | 1.5 | Slice 5 단독 비용 마진 5.5% (89.5%). 단순 임계 상향이 아니라 정책 재검토 (preset 외삽 시 비용 자연 증가) |

### B.4 Phase 2 위임

| # | 항목 | PS | 출처 |
|---|---|---|---|
| 12 | E6 분석 엔진 재계산 | 5.0 | Slice 4 신규, 슬라이스 분리 가능성 별도 검토 |

### B.5 누적 백로그 합

- Slice 5 진입 시점: ~13건
- Slice 5 신규 (Part 1/2): #19/#20/#21/#22 (+4)
- Slice 5 종결 발견: #β2 + #23 후보 (+2)
- Slice 5 처리: #11 완료 (-1), #β1 closed
- **Slice 5 종결 누적**: **~17건** (PS 합 ~21.5, Phase 2 #12 PS 5.0 제외 시 ~16.5)

---

## 부록 C — 회귀 카운트 진행 표 (Part 1 + Part 2 통합 실측)

| 단계 | 추가 (단독) | 누적 (단독) | 비고 |
|---|---|---|---|
| Slice 4 종결 | — | 173 | baseline |
| Slice 5 Part 1 Step 0~5 | +46 | 219 | Part 1 +46 (예상 +37 +9 초과 = 케이스 F, fixture parametrize 14건 효과) |
| **Part 1 종결** | — | **219** | (실측) |
| Part 2 Step 6 | 0 | 219 | smoke 산출물 |
| Part 2 Step 7 | +3 | 222 | token_budgets 단위 |
| Part 2 Step 8 | 0 | 222 | 회고 산출물 |
| Part 2 Step 9 | +10 | **232** | format_metrics_to_str + 단위 +10 (예상 +3 대비 커버리지 증가) |
| **Slice 5 종결 (실측)** | — | **232** | Slice 1·2·3·4·5 누적 +59 |

---

## 부록 D — 분석 엔진 의존성 회피 일관 적용 (Slice 1~5 누적)

E3 (Slice 5)도 Slice 1·3·4와 동일하게 분석 엔진 의존성 회피 정책 일관 유지:

| 항목 | Slice 5 적용 |
|---|---|
| E3 schema | analysis_context: dict (이미 산출된 MetricResult만 받음, 정량 재계산 없음) |
| build_e3_input | Core + Supporting 지표만 (Context 제외) — 산출 결과 조회만 |
| Mock 응답 | 자연어 코멘트만 (one_liner 10~300자) |
| fixture | 7개 모두 산출된 MetricResult 형태 |
| Step 6/8 LLM 호출 | LLM이 자연어 코멘트만 — 수치 검증 없음 |
| score_step8.py e3 entry | naturalness + insight + completeness만 평가 (정량 차원 미사용) |
| validation_report | §3 그룹 분석에서도 정량 비교 없음, 자연어 평가만 |

**5 슬라이스 모두 일관 적용** (E5 추출 진입점 포함). 누적 회피 비용은 Phase 2 백로그 #12 (PS 5.0)로 일괄 처리 또는 슬라이스 분리 위임.

---

## 부록 F — Slice 6 진입 결정 자료 (frame)

본 부록은 Slice 6 진입점 1순위 결정용. winner / insight 그룹차 등 manual eval 결과 도착 시 가중합 충전 → 1순위 확정.

### F.1 Slice 6 진입점 후보 비교표

#### F.1.0 가중치 산정 근거 (퀀트 5축)

가중치 합 = 1.00. 산정 근거 = *최종 산출물 가치 손실 기댓값 ÷ 1인 개발자 작업량* 비례 (Slice 5 부록 F.1과 동일 패턴):

| 축 | 가중치 | 산정 근거 |
|---|---|---|
| (1) Phase 2 product 시연 가치 | **0.20** | E4가 Coach 핵심 가치, 다른 후보는 인프라 정비 성격 |
| (2) 분석 엔진 의존성 / 인프라 위험 | **0.25** | 신규 인프라 도입 시 누적 부채 위험 |
| (3) Slice 5 패턴 재사용성 | **0.20** | _main_unified + format_metrics_to_str 즉시 활용 가능 여부 |
| (4) 비용 마진 적합도 | **0.15** | Slice 5 단독 마진 5.5%, 다음 슬라이스 매트릭스 규모 |
| (5) 1인 개발자 인지 부담 | **0.20** | 신규 Tier 분기 / preset 일반화 작업 복잡도 |

#### F.1.1 후보 점수표 (5점 만점, 1차 추정)

| 축 (가중치) | F.1.a E4 (대화 Q&A) | F.1.b preset 일반화 | F.1.c concentrated E3 | F.1.d LLMClient 통합 |
|---|---|---|---|---|
| (1) product 가치 (0.20) | 5 (Coach 핵심) | 3 (인프라) | 3 (E3 보완) | 1 (인프라 정비만) |
| (2) 의존성 위험 (0.25) | 2 (Tier 인프라 신규) | 4 (preset 인터페이스) | 5 (단독 schema 변경) | 5 (4 슬라이스 정비) |
| (3) Slice 5 재사용성 (0.20) | 3 (Tier 분기로 직접 활용 어려움) | 4 (preset 인터페이스 검증 결과 활용) | 5 (E3 패턴 그대로) | 2 (분기 본질 다름) |
| (4) 비용 마진 (0.15) | 3 (Tier 다층 시 호출 ↑) | 4 | 5 (단일 fixture) | 5 (LLM 호출 0) |
| (5) 인지 부담 (0.20) | 1 (매우 높음) | 3 (preset 일반화 설계) | 4 | 4 |
| **가중합 (winner 독립 추정)** | **2.85** | **3.55** | **4.40** | **3.45** |

#### F.1.2 winner 의존 가중합 보정 (manual eval 후 충전 완료)

**winner=haiku 확정** (efficiency 145% 우세, 글쓰기 가설 5/5 정착):
- E4 가중치 (1) +0.20 점 (Tier 2~3 default haiku 안전, product 가치 명확) → E4 가중합 **2.85 → 3.05**
- preset 일반화 가중치 (1) -0.10 점 (글쓰기 위험 해소로 우선순위 상대 ↓) → preset 일반화 **3.55 → 3.45**

**5 preset 외삽 insight 그룹차 = 1.8% (small_diff)** ✓
- preset 일반화 가중치 (3) +0.10 점 (insight 그룹차 ≤ 0.50, preset 일반화 안전) → preset 일반화 **3.45 → 3.55**
- 단 haiku robustness 입증으로 preset 일반화 *시급성* 약화 (해소된 위험은 우선순위 ↓)

**최종 가중합 (manual eval 후)**:

| 후보 | 가중합 (winner 독립) | 가중합 (winner=haiku 보정) | 최종 |
|---|---|---|---|
| E4 (대화 Q&A) | 2.85 | 3.05 | **3.05** |
| preset 일반화 | 3.55 | 3.55 (보정 상쇄) | **3.55** |
| concentrated E3 | 4.40 | 4.40 | **4.40** |
| LLMClient 통합 | 3.45 | 3.45 | **3.45** |

→ **1순위: concentrated_portfolio E3 (가중합 4.40)**, 2위 preset 일반화 (3.55) 대비 마진 +0.85.

**※ 본 보고서 §H의 UX 시나리오 5축 가중합과 별도 산출** — UX 시나리오 5축은 다른 가중치 (segment 크기 등)로 재산출 결과 4.05 vs 3.40, 결론 동일하게 concentrated E3 1순위.

#### F.1.3 1차 추정 1순위: **F.1.c concentrated E3** (가중합 4.40)

단 winner 결과로 변동 가능성 큼. manual eval 후 가중합 재산출하여 최종 결정.

특히:
- **winner=haiku** 시: E4 가중합 +0.20 ≈ 3.05 → 여전히 concentrated 1위 가능성. **준 1순위 추정: concentrated E3 또는 E4**
- **winner=sonnet** 시: preset 일반화 가중합 +0.20~+0.40 ≈ 3.75~3.95, concentrated 4.40 유지 → **여전히 concentrated 1위 추정**

→ 1차 추정 결론: **concentrated E3가 winner와 무관하게 1순위 가능성 높음**. manual eval 후 가중합 재검증.

### F.2 Slice 6 진입점 결정 영향 자료 (manual eval 도착 시 충전)

| 영향 자료 | 도착 시점 | 사용 |
|---|---|---|
| Step 8 winner (haiku/sonnet) | manual eval 후 | F.1.2 가중합 보정 |
| 글쓰기 가설 5/5 vs 4/5 외삽 | manual eval 후 | E4 진입 안전성 결정 |
| 5 preset insight 그룹차 | analyze_e3_groups.py 산출 후 | preset 일반화 안전성 결정 |
| Slice 5 단독 비용 추세 | 본 보고서 §F | 매트릭스 규모 산정 |

### F.3 Slice 6 Step 9 슬롯 후보

| # | 항목 | PS | 자연 흡수 가능성 (진입점별) |
|---|---|---|---|
| 19 | LLMClient.complete system 인자 추가 | 2.0 | E4: Medium / preset 일반화: Low / concentrated E3: High / LLMClient 통합: 본질 |
| 8 | LLMClient entrypoint 인자 + 가드레일 | 2.5 | 모든 진입점 High |
| 17 | auto_eval_e6.py 패턴 일반화 (E2 #10과 통합) | 2.0 | E4: High / preset 일반화: Medium / concentrated E3: Medium |
| 5 | TOKEN_BUDGET LLMClient 통합 잔여 | 2.0 | 모든 진입점 Medium |
| 14 | score_step8.py CLI 인자 확장 | 1.5 | 모든 진입점 High |

권장 슬롯 작업 (PS + 자연 흡수도 종합):
- E4 진입 시: **#17** (E4 사후 평가 자동화) 또는 **#8** (entrypoint 가드레일)
- preset 일반화 진입 시: **#8** (PS 2.5, 모든 진입점 적용)
- concentrated E3 진입 시: **#19** (E3 패턴 본질, 작업 자연 일관)
- LLMClient 통합 진입 시: 슬라이스 본질이 #19 → 슬롯은 **#5** 또는 **#14**

### F.4 Slice 6 Step 0 처리 후보

#### #β2 (PS 3.0): budget 1차 추정 모델 일반화

본 부채는 *Step 0에서 처리*가 자연. 작업 정의:

```python
# portfolio/llm/token_budgets.py 추가

def estimate_budget_for_entrypoint(
    entrypoint: str,
    sample_prompts: list[str],
    safety_factor: float = 1.5,
) -> int:
    """진입점별 1차 budget 추정.
    
    sample_prompts (3~5개)의 평균 토큰 수 × safety_factor → round-up 500.
    Slice 5 #β2 부채 처리 (PS 3.0).
    """
    from anthropic import Anthropic
    client = Anthropic()
    token_counts = [
        client.messages.count_tokens(...).input_tokens
        for p in sample_prompts
    ]
    avg = sum(token_counts) / len(token_counts)
    estimated = int(math.ceil(avg * safety_factor / 500) * 500)
    return estimated
```

작업량: 코드 1곳 수정 + 단위 테스트 +3~5건. **30분 한도 안전**.

### F.5 Slice 6 사전 결정 보존 권장 (slice6_decisions.md 작성 시)

```markdown
# slice6_decisions.md
> 작성일: (Slice 5 종결 시점 — manual eval 후)

## 진입점 결정
- 1순위: <concentrated E3 / E4 / preset 일반화 / LLMClient 통합>
- 가중합: <X.XX>
- 결정 영향 자료: winner=<haiku/sonnet>, insight 그룹차=<≤0.50/>0.50>, Slice 5 비용 추세=<>

## 진입점별 사전 결정
- concentrated E3 채택 시:
  - portfolio-level commentary schema 변경
  - Step 9 슬롯: #19 (LLMClient system 인자, E3 패턴 본질 일관)
- E4 채택 시:
  - Tier 1~3 fixture 신규 인프라
  - default provider: Tier 1 추출=sonnet / Tier 2~3 글쓰기=haiku (5/5 정착 시)
  - Step 9 슬롯: #17 또는 #8
- preset 일반화 채택 시:
  - 스코어링 엔진 일반화 작업
  - Step 9 슬롯: #8 (PS 2.5)
- LLMClient 통합 채택 시:
  - 4 슬라이스 호출처 일괄 정비
  - Step 9 슬롯: #5 또는 #14

## Step 0 #β2 처리
- estimate_budget_for_entrypoint() 헬퍼 도입
- 4 진입점 사전 검증 (e1/e2/e5/e6/e3 5종)
- 단위 테스트 +3~5

## 누적 결정 (Slice 1~5 보존)
- (Slice 1~5 결정 표 통합 — slice5_decisions.md 누적 결정 표 그대로)
```

---

## 부록 G — Slice 5 자동 단계 종결 시점 미해결 항목

### G.1 manual eval 의존부 (다음 turn 1턴에 일괄 충전)

| 산출물 | 빈칸 항목 |
|---|---|
| slice5_part2_report.md §D Step 8 | lex_pass_rate / label_means efficiency / Winner / efficiency 차이 / 그룹 분석 4매트릭스 / 글쓰기 가설 외삽 |
| slice5_part2_report.md §E F | 발동 / 미발동 |
| slice5_part2_report.md §G | 글쓰기 가설 외삽 검증 결과 |
| 부록 A | 4 행 (winner / lex pass / efficiency 차이 / 글쓰기 가설 외삽) + Slice 6 진입 결정 |
| 부록 F.1.2 | winner 의존 가중합 보정 |
| 부록 F.2 | 5 preset insight 그룹차 |

### G.2 충전 절차

1. 사용자 manual eval (`step8_2way_e3_raw.json` 14 entry) 입력
2. `python -m scripts.validation.score_step8 --entrypoint e3` → scored.json
3. `python -m scripts.validation.analyze_e3_groups` → group_analysis.json
4. 결과 첨부 → 본 산출물 빈칸 일괄 충전 + Slice 6 진입점 1순위 확정 + slice6_decisions.md 신설
