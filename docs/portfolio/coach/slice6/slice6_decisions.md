# slice6_decisions.md — Slice 6 진입 결정 기록 (Slice 5 완전 종결 시점)

> 작성일: 2026-05-07
> Slice 6 진입점 확정 + Step 0/9 슬롯 사전 결정 + Slice 6 Part 1 자료 회수 명세 5종 + Slice 7 사전 등록.

---

## §1. Slice 6 진입점 결정

### 1.1 결정 사항

**진입점**: **concentrated_portfolio E3 (portfolio-level commentary)**

**근거**:

- UX 시나리오 5축 가중합 4.05 (vs E4 3.40, 마진 +0.65)
- 자료 회수 가중합 4.40 (vs preset 일반화 3.55, LLMClient 통합 3.45, E4 3.05)
- Slice 5 자산 시간 비대칭성 (E3 패턴 따끈할 때 진입 유리)
- 인지 부담 최저 (E3 mirror)
- 부채 위험 0 (단독 schema 변경)
- Slice 5 haiku robustness 입증 (insight 그룹차 1.8% small_diff)으로 E4 지연 안전성 확보

### 1.2 영향 사용자 segment

| Segment                 | 시나리오                                                | 도달 시점                                  |
| ----------------------- | ------------------------------------------------------- | ------------------------------------------ |
| **집중 투자자 (5~10%)** | 5종목에 80% 집중한 사용자가 portfolio-level 코멘트 받음 | **Slice 6 종결 시 (1.5~2주)**              |
| 호기심 사용자 (30~40%)  | 자유 질문 대화형 답변                                   | **Slice 7 종결 시 (3~4주)** — E4 사전 등록 |

---

## §2. Slice 6 사전 결정

### 2.1 진입점 본질

**concentrated_portfolio preset의 portfolio-level commentary**:

- 입력: portfolio-level Core 지표 7종 (Slice 5 자료 #2 인용)
  - hhi_concentration (허핀달-허쉬만 지수)
  - sector_hhi (섹터 집중도)
  - top3_weight (상위 3종목 비중)
  - holding_count (보유 종목 수)
  - portfolio_beta (포트폴리오 베타)
  - max_position_weight (최대 포지션 비중)
  - avg_correlation (평균 상관계수)
- 출력: portfolio-level commentary (one_liner per metric, 단 종목별이 아니라 _포트폴리오 전체_ 차원)

**E3와의 차이**:

- E3 (Slice 5): 종목별 metric 코멘트 (예: "Apple의 P/E는...")
- Slice 6 진입점: 포트폴리오 차원 코멘트 (예: "당신의 포트폴리오는 통제된 집중 위험을 보입니다 — 상위 3종목에 65% 노출")

**fixture 전략 후보** (Part 1 결정 필요):

- 옵션 A: hybrid 5 (baseline 2 + focused 3) — Slice 5 패턴 mirror 축소
- 옵션 B: 단일 매트릭스 5 fixture (concentrated 강도 차등 — high/mid/low concentration)
- 옵션 C: hybrid 7 그대로 (Slice 5 mirror 100%) — 단 concentrated_portfolio preset만 적용 가능 fixture

### 2.2 Step 0 = #β2 (확정)

**작업**: budget 1차 추정 모델 일반화 (PS 3.0)

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
        client.messages.count_tokens(
            model=ANTHROPIC_HAIKU_MODEL,
            messages=[{"role": "user", "content": p}],
        ).input_tokens
        for p in sample_prompts
    ]
    avg = sum(token_counts) / len(token_counts)
    estimated = int(math.ceil(avg * safety_factor / 500) * 500)
    return estimated
```

**작업량**: 코드 1곳 수정 + 단위 테스트 +3~5건 (e1/e2/e5/e6/e3 5 진입점 사전 검증). **30분 한도 안전**.

**예상 효과**: 진입점별 prompt 구조 자동 반영 → Slice 6 concentrated E3에서 1차 추정 정확도 ±20% 이내 가능.

### 2.3 Step 9 슬롯 = #19 (확정)

**작업**: LLMClient.complete system 인자 추가 (default None) + 4슬라이스 호출처 일괄 정비 (PS 2.0)

**자연 흡수 가능성**: concentrated E3는 prompt 구조가 system + few-shot examples 패턴 — Slice 5와 동일. 본 슬라이스에서 자연 정비 가능.

**작업 정의**:

1. `LLMClient.complete(prompt, *, system: Optional[str] = None, ...)` 시그니처 변경
2. Slice 1·3·4·5 호출처 4건 일괄 정비:
   - Slice 1 E1: system 인자 도입 안 함 (기존 단일 prompt 유지)
   - Slice 3 E2 / Slice 4 E6 / Slice 5 E3: build\_\*\_prompt이 단일 str 반환 → system 분리 가능 시 정비
3. service `build_e3_prompt` wrapper 제거 (Slice 5에서 임시 도입한 concat 패턴 → system 인자 직접 전달)
4. 단위 테스트: 4 진입점 + system 인자 default None 처리

**부채 #21 (deprecated wrapper 제거) 자연 흡수 가능성**: 별개 작업 (#21은 format_metrics_table wrapper 제거, #19와 무관). Slice 7+ 이연.

### 2.4 평가 차원 + winner 가설

- **평가 차원**: naturalness + insight (manual) + completeness (자동) — Slice 5 mirror
- **default provider**: haiku (글쓰기 가설 5/5 정착, 영구 정책)
- **winner 가설**: haiku 6번째 외삽 (preset 외삽 robustness + portfolio-level commentary 추가 검증)

### 2.5 매트릭스 + 비용

- **Step 8 매트릭스**: 7 fixture × 2 model = 14 calls (Slice 5 mirror, gemini 제외)
- **비용 임계**: $0.20 (현재 임계 유지, 단 마진 5.5%로 좁음 → 백로그 후보 #23 검토)
- **CostGuard**: slice_id="slice6", 호출 한도 50

---

## §3. Slice 6 Part 1 자료 회수 명세 5종

다음 세션 진입 시 클로드 코드에 즉시 전달 가능한 형식. Slice 5 Part 1 자료 회수 패턴 mirror.

### 3.1 회수 템플릿

```
[Slice 6 Part 1 작성 직전 자료 회수 — 5종]

#1 concentrated_portfolio Core 지표 7종 인터페이스
   - portfolio/metrics/definitions/preset_metrics.py 내 concentrated_portfolio preset 정의 발췌
   - 7종 Core 지표 정의 (hhi_concentration / sector_hhi / top3_weight / holding_count / portfolio_beta / max_position_weight / avg_correlation)
   - 각 지표의 percentile_scope (universe / sector / industry) 적용 여부
   - direction_override 적용 여부 (concentrated_portfolio는 일부 지표가 lower_is_better → higher_is_better override 가능성)
   - 산출 시점 (실시간 vs 사전 계산)
   - portfolio-level metric의 5단계 level_tag 적용 방식

#2 portfolio-level commentary schema 후보
   - Slice 5 MetricComment / MetricComments schema (portfolio/schemas/llm_outputs.py:65-87) 그대로 활용 가능 여부
   - 또는 신규 PortfolioMetricComment 추가 필요 여부 — portfolio_id 필드 추가 등
   - one_liner의 metric_id가 portfolio-level metric (예: "hhi_concentration")인 경우 schema 통과 여부
   - 기존 metric_id naming convention (snake_case)과 일관성

#3 concentrated_portfolio fixture 7건 작성 가능성
   - 실제 종목 데이터 vs synthetic 데이터 권장
   - high concentration (top3 ≥ 70%) / mid (40~70%) / low (≤ 40%) 강도 차등 가능성
   - sector concentration vs stock concentration 분리 fixture 가능성
   - hybrid 전략 (baseline + focused) 적용 가능 여부

#4 #β2 estimate_budget_for_entrypoint 도입 가능성
   - portfolio/llm/token_budgets.py 현재 구조 (Slice 5 종결 시점)
   - count_tokens API 호출 비용 (generation 비용 0이므로 안전, 단 호출 시간)
   - 4 진입점 sample_prompts 사전 준비 가능성 (e1/e2/e5/e6 각 1~3개)
   - Step 0 30분 한도 내 작업 적합도

#5 #19 LLMClient.complete system 인자 도입 영향도
   - 현재 LLMClient.complete 시그니처 (Slice 5 종결 시점)
   - 4슬라이스 호출처 grep 결과 (e1 / e2 / e6 / e3 service 각각의 build_*_prompt 호출부)
   - system + user 분리 가능 여부 (Slice 5 build_e3_prompt wrapper 제거 + raw build_e3_prompt 직접 활용)
   - 회귀 위험: Slice 1·3·4·5 IDENTICAL hash 영향 가능성 (없을 것으로 예상하나 검증 필요)
```

### 3.2 회수 시점

- 다음 세션 시작 시 1회 회수 (자료 #1~#5 동시 첨부 권장 — Slice 5 Part 1 진입 시와 동일 패턴)
- 회수 결과 도착 시 → Slice 6 Part 1 결정 사이클 (Q1~Q? 옵션 분석) → 본 지시서 작성

---

## §4. Slice 6 KPI 사전 잠금

### 4.1 핵심 KPI

- **회귀 단독 +35~45** (Slice 5 +59 mirror, 단 portfolio-level은 fixture 적은 경우 변동 가능)
- **Slice 1·3·5 IDENTICAL hash 보장**: Step 9 #19 통합 후 4슬라이스 hash 변경 0
  - Slice 1: `917fa3ef821426e88178456a1f70462f5ab9576e20f06a63d0a88c28fcc0f7b9`
  - Slice 3: `5594c6ab9291213bca7d3e98b3b221164575eb47c52a281248ddc616218cf3ba`
  - Slice 5: (Slice 5 종결 시점 hash 별도 회수 필요)
- **글쓰기 가설 6번째 외삽**: winner=haiku → 6/6 정착, sonnet → 5/6 재평가 (케이스 F)
- **CostGuard 한도** ≤ 18/50 (예상 15)
- **Slice 6 단독 비용** ≤ $0.20 (마진 5.5% 좁음, #23 검토)

### 4.2 KPI 12/12 목표

자동 8 + manual 4 = 12 KPI (Slice 5 mirror).

---

## §5. Slice 7 사전 등록

### 5.1 진입점

**E4 대화 Q&A (Tier 1~3)**

### 5.2 사전 결정

- 호기심 사용자 segment (30~40%) 도달
- Tier 1 (사실 확인) / Tier 2 (해석) / Tier 3 (조언) 다층 분기
- default provider:
  - Tier 1 (추출): sonnet (Slice 2 E5 패턴)
  - Tier 2~3 (글쓰기): haiku (5/5 정착 + Slice 6 6번째 외삽 결과 반영)
- Step 9 슬롯 후보: #17 auto_eval_e6 패턴 일반화 (E4 사후 평가 자동화에 자연 흡수, PS 2.0)
- 매트릭스: Tier별 fixture 신규 인프라 필요

### 5.3 Slice 7 진입 시점 검토 항목

- Slice 6 winner (haiku 6/6 정착 vs 5/6 재평가)
- Slice 6 portfolio-level robustness (insight 그룹차)
- 누적 비용 ($0.764 + Slice 5 + Slice 6 = ~$1.0 예상, 수익화 진입 검토)

---

## §6. 누적 결정 (Slice 1~5 + Slice 6 진입)

```
Slice 1: E1 + GARP (winner=haiku)
Slice 2: E5 추출 (winner=sonnet, 가설 일관 반례)
Slice 3: E2 4요소 카드 (winner=haiku)
Slice 4: E6 비교 해설 (winner=haiku)
Slice 5: E3 지표 코멘트 + preset 외삽 (winner=haiku, 5/5 정착, robustness 1.8% small_diff)
Slice 6: concentrated_portfolio E3 portfolio-level (진입 결정 ✓)
Slice 7: E4 대화 Q&A (사전 등록)
Phase 2: 분석 엔진 #12 (PS 5.0 위임)
```

영구 정책:

- 글쓰기 진입점 default provider = haiku (5/5 정착)
- 광의 단일 비용 정책 (COST_POLICY.md, Slice 5+ 적용)
- 분석 엔진 의존성 회피 (Phase 2 위임)
- \_main_unified DIMENSION_LOOKUP 1줄 entry 자동 dispatch
- IDENTICAL hash KPI (Slice 1·3·5·... 누적 보장)

---

## §7. 다음 세션 첫 메시지 권장 형식

```
[Slice 6 Part 1 진입 — 자료 회수 결과 첨부]

#1 concentrated_portfolio Core 지표 7종 인터페이스: ...
#2 portfolio-level commentary schema 후보: ...
#3 concentrated_portfolio fixture 7건 작성 가능성: ...
#4 #β2 estimate_budget_for_entrypoint 도입 가능성: ...
#5 #19 LLMClient.complete system 인자 도입 영향도: ...

Slice 6 Part 1 결정 사이클 진입.
```

→ Claude는 자료 + 본 slice6_decisions.md를 baseline으로 즉시 결정 사이클 진입 (Q1 fixture 전략 / Q2 schema 활용 / ...) → Slice 6 Part 1 본 지시서 작성.
