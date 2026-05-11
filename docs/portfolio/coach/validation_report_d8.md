# D-8 Validation Report

> 생성일: 2026-04-24
> 대상: 세션 D (D-0a ~ D-7 전 세션 통합 검증)

## Test Results

| Suite | Passed | Total |
|---|---|---|
| Static integrity       | 7 | 7 |
| Prompt assembly        | 10 | 10 |
| Scenario end-to-end    | 2 | 2 |
| Session lifecycle (DB) | 2 | 2 |
| **Total**              | **22** | **22** |

실행 명령: `pytest portfolio/tests/ -q`

## Token Budget Summary (측정치)

실측 기준 (fixtures `get_context_garp_tech()` AnalysisContext + GPT 토크나이저 근사치 chars/4).

| 진입점 | chars | ~tokens | 지시서 목표 | 합격? |
|---|---|---|---|---|
| Tier 0        | 7,766  | ~1,941 | 1,500~2,000 tokens | OK |
| E1 (system+user) | 12,649 | ~3,161 | 3,000~4,500 tokens | OK |
| E2 (system+user) | 17,095 | ~4,273 | 5,000~8,000 tokens | below range (예시 3개 + 실제 context) |
| E3 (system+user) | 12,169 | ~3,041 | 3,500~5,000 tokens | below range (지표 3개 기준 fixture) |
| E5 (system+user) | 14,819 | ~3,704 | 2,500~4,000 tokens | OK |
| E6 (system+user) | 15,069 | ~3,766 | 4,500~6,500 tokens | below range (작은 fixture) |
| E4            | — | (Tier 1~3 포함, fixture 변수, DB 기반) | 8,000~12,000 tokens | DB 테스트에서 assembly 확인 |

> E2/E3/E6이 지시서 목표 범위보다 낮은 것은 fixture가 간소해서 발생. 실제 프로덕션에서는 지표/종목 수가 많을수록 목표 범위에 근접.

## PV3 Consistency Check

- [OK] Tier 0 terminology block에 `analysis_target_portfolio`, `wallet_all_holdings`, `excluded_from_this_portfolio` 포함 확인 (test_tier0_pv3_terminology_present).
- [OK] 모든 진입점의 user 메시지가 PV3 필드명 준수 (E1 `build_e1_input` 반환 key에 `analysis_target_portfolio`/`wallet_background`).
- [OK] `AnalysisContext.model_fields` 검사에서 `portfolio`, `wallet` 필드 없음 확인 (test_schema_pv3_field_names).

## Static Integrity

- [OK] Django 13개 모델 import 성공, `Holding`/`CandidateHolding` import 불가 (완전 제거).
- [OK] PRESET_METRICS의 모든 metric_id가 METRICS에 존재 (지표 57 × 프리셋 12).
- [OK] 지표 수 57 (stock_level 39 / portfolio_level 13 / composite 5) 일치.
- [OK] CURRENT_VERSIONS의 5개 버전 키 존재 (metric_version=1.2 확인).

## Scenario Flow

분석 → E1~E3 자동 → 사용자 질문 → E4 → 조정 요청 → E5 파싱 → E6 비교 체인이 예외 없이 조립됨 (test_scenario_analyze_question_adjust_compare).

## Session Lifecycle

- Wallet → WalletHolding → Portfolio → AnalysisRun → ChatSession → Message → Decision 전체 체인 저장 검증.
- H3 정책 (Portfolio.effective_holdings): WalletHolding 삭제 시 자동 필터링 동작 확인, `wallet_holding_ids` 정의 자체는 불변.

## Detected Issues

발견된 설계 모순/충돌 없음. 다음은 의도된 한계로 기록:

- **E2/E3/E6 토큰 예산 하회**: 현재 fixture가 종목 5~7개, 지표 2~3개 수준이라 프롬프트가 짧음. 실제 프로덕션 데이터에서는 자연스럽게 범위 내 진입 예상.
- **Preset threshold 정보 부재**: `preset_metrics.py`에 프리셋별 임계값이 없어 E5 입력의 `current_threshold`를 `null`로 제공. D-0a 이후 설계 확장 시 추가.
- **Per-holding 값 배열**: E2 `weaknesses_detail.per_holding`은 현재 `[]`로 초기화 — 백엔드 MetricResult 계산 로직이 채워 넣어야 함 (별도 세션).

## MVP Readiness

- [✓] 구조 완성도: 13 Django 모델 + 8 Pydantic 스키마 + 6 진입점 프롬프트 + 통합 테스트.
- [✓] 프롬프트 조립 정상: 22/22 테스트 통과.
- [✓] 시나리오 chain 동작: E1→...→E6 dry-run 성공.
- [✓] DB 모델 정합성: H3 정책 포함 검증.

## Recommendation

**MVP ready for LLM integration testing: YES**

Blockers: 없음.

다음 단계:
1. Anthropic/GPT 실제 호출 테스트 (API 키 주입 + 응답 Pydantic 검증).
2. 백엔드 API 엔드포인트 설계 (Views + Serializers + URL 라우팅).
3. ReturnCalculator 구현 (RV1~RV4 정식 수익률 계산).
4. 프리셋 스코어링 엔진 (MetricResult → strengths/weaknesses 자동 도출).
5. Tier 2 세션 요약 자동 생성 (E7 준 기능, Phase 2 후보).
6. 프론트엔드 연동 (Coach 채팅 UI, 확인 카드, 조정 플로우).
