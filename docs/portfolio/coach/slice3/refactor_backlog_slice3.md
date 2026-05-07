# Slice 3 Refactor Backlog (Slice 4 이연)

> 작성: 2026-05-07
> 정책: P × R × S / C 우선순위

## Slice 2에서 이연된 항목 (재정리)

| # | 항목 | PS | 출처 | 예상 시간 | Slice 3 처리 여부 |
|---|------|-----|------|-----------|------------------|
| 2 | score 산식 통합 (e1 동적 + e5 정적 + e2 추가) | 3.0 | Slice 2 #2 | 60분 | **이연** (Slice 4) |
| 3 | PROVIDER_KWARGS services 공유 모듈 | 2.0 | Slice 2 #3 | 20분 | **완료** (Slice 3 Step 2 흡수) |
| 4 | build_*_prompt 헬퍼 분리 | 2.0 | Slice 2 #4 | 15분 | **완료** (Slice 3 Step 2 흡수) |
| 5 | E5_TOKEN_BUDGET 상수 + LLMClient 가드레일 | 2.0 | Slice 2 #5 | 30분 | **부분 완료** (token_budgets.py 신설, LLMClient 통합 이연) |
| 6 | Step 8 raw output CSV 옵션 | 1.0 | Slice 1 deferred #7 | 10분 | **이연** |
| 7 | Mock LLMClient mode dict 매핑 | 1.0 | Slice 1 deferred #8 | 10분 | **이연** |

## Slice 3 신규 발견

| # | 항목 | PS | 출처 | 예상 시간 |
|---|------|-----|------|-----------|
| 8 | LLMClient에 entrypoint 인자 추가 + 입력 가드레일 통합 | 2.5 | Slice 3 Step 9 미완 | 20분 |
| 9 | latency 임계 5,000ms → 16,000ms 상향 (E2/추후 글쓰기 진입점) | 2.0 | Slice 3 Step 6/8 발견 | 5분 |
| 10 | E2 자동 평가 keyword_match 룰 보완 (의미적 매칭 추가) | 1.5 | Slice 3 Step 8 자동 평가 | 30분 |
| 11 | _prompt_helpers.format_metrics_table 일반화 (현재 E2 specific) | 1.5 | Slice 3 Step 2 작성 시 | 15분 |
| 12 | DiagnosticCard 4요소 가중치 (현재 균등) — 사용자 피드백 후 | 조건부 | Slice 5 Phase 2 | 30분 |
| 13 | LLM-as-judge 도입 (Phase 2) — 자동 naturalness/insight 판정 | 5.0 | Slice 5 Phase 2 | ~6시간 |

## Slice 4 Step 9 슬롯 권장 (30분 한도)

**1순위**: #8 LLMClient entrypoint 가드레일 (20분) + #9 latency 임계 (5분) — 합산 25분, 한 PR

**2순위**: #2 score 산식 통합 (60분 — 한도 초과, Slice 4 별도 큰 PR)

**3순위 (Slice 5)**: #13 LLM-as-judge — 가장 큰 가치, 별도 슬라이스 필요

## Slice 1 미해결 (재확인)

- garp_large fixture 토큰 효과 측정 — Slice 3 Step 7에서 검증 (15 holdings 베이스 686 tokens)
- gemini Flash paid tier 활성화 시 재비교 — 보류 (Slice 1/2/3 모두 anthropic 사용)

## 결정 근거 메모

**Slice 3에서 #3, #4 흡수 결정 (A2.C)**:
- E2 service 신설 시점에 자연 흡수 — 별도 PR 비용 0
- Slice 4 진입 시 신규 진입점도 동일 패턴 사용 → 재사용 효과 극대화

**Slice 3에서 #5 부분 완료 결정**:
- token_budgets 상수 도입은 30분 슬롯 한도 안 (실제 ~15분)
- LLMClient 인터페이스 변경 (entrypoint 인자)은 모든 service 호출 갱신 필요 → Slice 4 별도 처리
- 분리 이유: 슬롯 한도 보존 + Slice 1/2/3 service 갱신 회귀 비용 격리
