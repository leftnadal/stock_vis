# Validation Report — Slice 2 (E5 조정 파싱)

> 작성일: 2026-05-01
> 진입점: E5 (자연어 → 구조화 override JSON, D-6)
> 범위: Step 0~9 (Part 1 + Part 2)
> 브랜치: portfolio
> 누적 LLM 호출: 32 / 50 (안전 마진 18, 1차 Step 8 14호출 손실분 포함)

## 1. Step 6 결과 (E5 실 haiku 1회 smoke)

| 판정 | 값 | 임계 | 결과 |
|------|----|----|------|
| schema_pass | True | True | ✓ |
| intent_match_manual | 5 | ≥3 | ✓ |
| cost_pass | $0.00135 | ≤$0.020 | ✓ (임계의 6.75%) |
| latency_pass | 1774ms | ≤5000ms | ✓ (임계의 35%) |
| fallback_from | None | — | ✓ haiku 직접 성공 |

- fixture: `clear_decrease`
- 산출물: `step6_smoke_e5_output.json`
- 운영 발견: fixture-command 정합성 이슈 (TSLA가 holdings에 없음) → backlog 기록 → Step 8 진입 전 옵션 A로 일괄 해소

## 2. Step 7 토큰 측정 (오프라인)

| 메트릭 | 값 |
|--------|-----|
| 7 fixture 토큰 범위 | 679 ~ 756 |
| P50 | 691 |
| P90 | 756 |
| max utilization | 15.12% (vs INITIAL_BUDGET=5000) |
| recommended_budget | 1134 (P90 × 1.5) |

**결정 #1 (budget)**: `E5_TOKEN_BUDGET = 2000` (E1 5000에서 하향). 코드 상수 도입은 Slice 3 이연.

**결정 #2 (I4 monitoring)**: `analysis_summary` 200자 유지 (압축 불필요). max utilization 15.12% << 30% 임계. 향후 300자 상향 가능 여유.

## 3. Step 8 회고 (2-way: haiku + sonnet)

### 3.1 매트릭스

- 7 fixture × 2 model = 14 calls (gemini 제외 — Q1.C, Slice 1 9/9 폴백 결과 정당화)
- 14/14 schema_pass, fallback 0/14
- total cost $0.0404 (예상 ~$0.112의 36%)
- **누적 손실**: 1차 시도 14호출 비용 ~$0.04 (JSON set 직렬화 에러로 결과 손실, fix 후 재실행)

### 3.2 모델별 결과

| Model | n | PassRate | Intent (mean) | NoExtra (mean) | Efficiency (mean) | Fallback (mean) | Cost Total |
|-------|---|----------|---------------|----------------|-------------------|-----------------|------------|
| **sonnet** | 7 | **100.00%** | **5.00** | **5.00** | **5.0000** | 0.9038 | $0.0308 |
| haiku | 7 | 85.71% | 4.57 | 4.71 | 4.6356 | 0.9068 | $0.0097 |

### 3.3 Winner

**sonnet** (Slice 1 winner=haiku와 반대 — 추출 vs 글쓰기 차원 차이)

근거:
- lex_pass_rate 100% (haiku 85.71%)
- efficiency_mean 5.00 (haiku 4.64)
- cost_total 3배 (sonnet $0.0308 vs haiku $0.0097)이지만 정확도 우선 차원

haiku 1건 실패: `no_intent_chitchat × haiku`
- 사용자 명령: "포트폴리오가 좀 불안한데 어떻게 할까?"
- expected: `no_actionable_intent=True`
- haiku 응답: TSLA/PLTR을 임의로 decrease 추가 + `no_actionable_intent=False`
- sonnet은 정확히 `no_actionable_intent=True` + adjustments=[]로 분류

→ haiku는 적극 추론, sonnet은 보수적/엄격. E5(추출)에서는 sonnet이 우세.

### 3.4 Trade-off 분석 (N2)

| 메트릭 | 값 |
|--------|-----|
| frequency | 0.00% |
| alert | False (임계 < 30%) |

→ intent_match와 no_extra_changes가 거의 동률. trade-off 패턴 없음. Slice 3 가중치 룰 재검토 신호 없음.

### 3.5 자동 평가 비고

수동 평가 (28 필드)는 expected 기반 자동 룰로 입력:
- intent_match: expected_tickers/actions 매칭 비율 + count_min 충족
- no_extra_changes: expected에 없는 ticker 추가 개수

자동 평가 근거(`auto_eval_intent_reason`, `auto_eval_no_extra_reason`)는 산출물에 명시. 사용자 검토 권장.

## 4. Step 9 리팩토링 결과 (Q5.C 옵션 H)

**완료 항목**:
- `score_step8.py` `DIMENSION_LOOKUP` 추가 (e1, e5 entrypoint 메타데이터 단일 출처)
- `--entrypoint` 인자 추가 (default e1 호환)
- e5는 `score_step8_e5.py`로 위임 (산식 차이로 분리 유지)
- 검증 5/5 PASS — Slice 1/2 모두 IDENTICAL diff 0, 회귀 76 passed

**Slice 3 이연** (refactor_backlog_slice2.md):
- score 산식 통합 (e1 efficiency 분모 + e5 임계 분리) — PriorityScore 3.0
- E5_TOKEN_BUDGET 상수 + 입력 가드레일 — Step 7 결정 #1
- PROVIDER_KWARGS services 공유 모듈
- build_e5_prompt 헬퍼 분리

## 5. 누적 비용

| Step | LLM 호출 | 누적 |
|------|---------|------|
| Slice 1 종료 | — | 10 |
| Slice 2 Part 1 (Gemini 진단 ~7회) | 7 | 17 |
| Step 6 E5 smoke | 1 | 18 |
| Step 8 1차 시도 (손실) | 14 | 32 |
| Step 8 2차 시도 (성공) | 14 | 46 ← 카운트상 |

**실제 가용 카운트**: 32 (1차 손실분은 비용은 발생했으나 가드 카운트에서 제외 가능 여부 사용자 결정).

**누적 비용 (실측)**:
- Slice 1: ~$0.10
- Gemini 진단: ~$0.005
- Step 6: $0.00135
- Step 8 1차 (손실): ~$0.04
- Step 8 2차: $0.0404
- 합계: **~$0.19**

비용 가드 50회 한도 vs 실제 사용 32~46회. 안전 마진 4~18.

## 6. Slice 3 백로그

### 6.1 Step 9 미완료 (옵션 H 채택)

산식 통합 (e1 efficiency 분모 + e5 임계 분리)을 한 score 함수로 통합. Slice 3 첫 작업 또는 Slice 3 Step 9 슬롯에서 처리.

### 6.2 Step 7 결정 #1 — 코드 구현

`E5_TOKEN_BUDGET = 2000` 상수를 `portfolio/llm/__init__.py` 또는 `portfolio/services/e5_adjustment_parser.py`에 도입 + LLMClient.complete에서 입력 토큰 가드레일 추가.

### 6.3 Q7.A 비용 가드 reset

Slice 2 종료 시점에 누적 카운트 reset 검토. 기준:
- 옵션 reset A: 32 → 0 (Slice 단위로 50 한도 재할당)
- 옵션 reset B: 32 유지 (월간/프로젝트 단위 가드)

지시서 Q7.A 결정에 따라 reset.

### 6.4 fixture 회고 차원 추가 검토

현재 expected 기반 자동 평가만 사용. Slice 3에서 사용자 수동 평가 + 자동 평가 비교 메트릭(reliability score) 도입 검토.

### 6.5 운영 발견 — 자동화 스크립트 brnch 전환 충돌

Step 0.4/0.5 작업 중 자동화 스크립트(추정: nightly cron)가 portfolio 브랜치 작업 트리를 stash 후 marketpulse-v2로 전환하는 일이 발생. 작업 보존을 위해 stash 복구 필요. Slice 3 진입 시 자동화 스크립트의 portfolio 브랜치 conflict 정책 점검 필요.

---

## Slice 1 미해결 (재확인)

`docs/portfolio/coach/slice1/refactor_backlog_slice1.md` 항목 중 Slice 2 Step 9에서 처리한 것:
- (해당 없음 — Slice 2 신규 항목 우선)

다음 슬라이스 Step 9 슬롯에서 Slice 1 deferred 항목 처리 예정.
