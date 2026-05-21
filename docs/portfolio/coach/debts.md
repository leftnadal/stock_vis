# Portfolio Coach 부채 대장 (Slice 13 Part 1 진행 중)

**최종 갱신**: 2026-05-21 (Slice 13 Part 1 — E1 DRF endpoint + contract test)
**관리 원칙**: 매 슬라이스 종결 시 갱신. close/keep_open/신규 변동 명시.

---

## §1. 현재 OPEN 부채

### #51: output_token estimator multivariate (Slice 13 Step 0a fit close, integration #62로 분리)

- **history**:
  - Slice 11 Part 1: 본격 구현 (8 진입점 char ratio 단변량 fit) — max 33.12%, P90 11.20%, mean 5.11%
  - **Slice 13 Step 0a: multivariate OLS fit 도입** (`tokens = a + b × chars`, (EP, model) lookup)
    - 백테스트 결과: mean 5.11→4.40, P90 11.20→9.52, **max 33.12→24.58** (−8.54)
    - e4_conversation max 대폭 개선 (−16.18)
    - rationale max −3.45
- **현재 상태**: **fit 부분 close** (정확도 개선 검증 완료) — integration은 #62로 분리
- **남은 작업**: CostGuard에 estimate_output_tokens 호출 경로 연결 — Slice 13 Step 0b에서 처리 (#62)

### #61: 3단 게이트 경계값 calibration (Slice 14, PS 2.5)

- **신규 등록**: Slice 13 Step 0a (2026-05-21)
- **history**:
  - Slice 13 Step 0a #60: ADDITIVE 3단 게이트 (`gate_tiers` 필드 + `_evaluate_gate_tier`) 도입
  - 현재 12 preset 모두 `gate_tiers=None` (PLACEHOLDER 상태) — 평가 항상 "pass" (점수 경로 무손상)
- **작업 범위**:
  - 12 preset별 fail_below / warn_below 경계값 실측 분포 기반 calibration
  - 옵션 B threshold (기존 단일 `gate`)와 통합 가능성 검토 → 2-tier vs 3-tier 데이터 검증
  - LLM commentary에 gate_tier 주입 시 품질 변화 측정 (manual eval)
  - **estimator 정밀화와 함께 `PRE_CALL_SAFETY_BUFFER` 계수 재조정 대상**
    (현재 1.25 = max delta 24.58% 흡수, #51 추가 개선 시 buffer 축소 가능)
- **참조**: `portfolio/services/scoring/preset_spec.py` (gate_tiers schema),
  `portfolio/services/scoring/base.py::_evaluate_gate_tier`,
  `portfolio/llm/cost_guard.py::PRE_CALL_SAFETY_BUFFER`

### #63: 누적 비용 ledger 영속화 (Slice 14+, PS 1.5)

- **신규 등록**: Slice 13 Step 0a (2026-05-21)
- **history**:
  - Slice 8+에서 슬라이스 누적 비용 추적은 closing 보고서에 수기 기재 ($3.1196 등)
  - **ledger 파일 자체가 미존재** — slice 간 연속 누적값 검증 불가
- **작업 범위**:
  - JSONL 또는 SQLite ledger 파일 (예: `docs/portfolio/coach/cost_ledger.jsonl`)
  - LLM 호출당 1행: timestamp, model, input/output_tokens, cost_usd, slice, source_file
  - CostGuard.reset_for_slice() 시 ledger flush + slice 합계 출력
  - #62와 인프라 묶음 처리

### #65: 기존 순수 Django view 최종 처리 (Slice 13 후반 Part, PS 1.5)

- **신규 등록**: Slice 13 Part 1 (2026-05-21)
- **history**:
  - Slice 13 Part 1: E1 DRF endpoint (`/api/coach/e1/`) 추가, 기존 `coach/e1/garp/` 무수정 유지
  - E1만 마이그레이션 완료, E2~E6는 후속 Part에서 동일 패턴 확장
- **선행 조건**:
  - E1~E6 6개 endpoint 전체 DRF 마이그레이션 완료
- **작업 범위 (선행 완료 후)**:
  - 기존 순수 view (`portfolio/views.py`, `portfolio/urls.py`) **유지 / 제거 / wrapper화** 결정
  - 클라이언트 호출 경로 분석 (frontend, 자동화 스크립트)
  - wrapper화 선택 시: 순수 view → DRF endpoint 호출로 위임 (이중 라우팅 제거)
- **참조**: `portfolio/api/` (신규 DRF 패키지), `portfolio/views.py` (legacy)

### #64: 사전 추정 기반 blocking 차단 모드 (Slice 14+, PS 1.0)

- **신규 등록**: Slice 13 Step 0b (2026-05-21)
- **history**:
  - Slice 13 Step 0b #62: estimator→CostGuard non-blocking 경고 모드 도입 (WARNING 로그만)
  - blocking 차단 (예산 초과 추정 시 raise)은 **분리 부채로 이연**
- **이연 사유**:
  - estimator max delta **24.58%** (Slice 13 Step 0a 백테스트) — 차단 켜면 정상 호출 오탐 차단 위험
  - #61 (gate calibration) + #51 (estimator 추가 개선) 진행 후 buffer 축소 가능 시점에 검토
- **작업 범위**:
  - `check_pre_call_budget()` 결과 기반 raise (`CostCapExceeded` / `CostThresholdExceeded`)
  - opt-in 설정 (env `PRE_CALL_BLOCKING=true` 등) — 기본 off
  - 실측 delta 모니터링 후 blocking 안전 임계 도출
- **단서**: "estimator delta 24.58% → #61 calibration 후 차단 안전"
- **참조**: `portfolio/llm/cost_guard.py::check_pre_call_budget`

### #59 (open / E5 잔여): action_items measurability — E5 진입점 (PS 0.5)

- **history**:
  - Slice 11 Part 5 발견: E3 50%, E5 25%, E1 0% NG
  - Slice 12 Step 0b: **E3 close** (prompt 보강 후 NG 0%)
  - **잔여**: E5 25% NG (1/4) — Slice 13+ 검토
- **처리 방향**: E5 micro-matrix 측정 후 prompt 보강 (#59 패턴 재사용 가능)

### #57: KPI 임계 보정 (close, Slice 11 Part 5 D5-A 적용)

- Slice 11 Part 5에서 **close**. KPI spec 갱신 완료 (`kpi_matrix.md`).
- 슬라이스 유형별 회귀 +Δ 임계 (매트릭스 슬라이스 +10~15, manual eval +2~5).

---

## §2. 최근 슬라이스 CLOSE 부채 (Slice 12 Step 0 + Slice 13 Step 0a/0b/Part 1)

### #62: estimator → CostGuard integration (close, Slice 13 Step 0b)

- **history**:
  - Slice 13 Step 0a: 신규 등록 (PS 1.5)
  - Slice 13 Step 0b: **close** — non-blocking 경고 모드로 도입 완료
- **구현**:
  - `portfolio/llm/cost_guard.py::estimate_call_cost()` 신규 메서드
    (estimator_v3 input/output 추정 → Anthropic 단가 환산)
  - `PRE_CALL_SAFETY_BUFFER = 1.25` 상수 (estimator max delta 24.58% 흡수)
  - `check_pre_call_budget()` — 예산 초과 추정 시 WARNING 로그만 (non-blocking)
- **단위 테스트**: 12/12 PASS (비용 산정 4 + buffer + non-blocking 3 + 기존 동작 불변 3)
- **IDENTICAL 보호**: 31/31 PASS (non-blocking으로 LLM 호출 경로 영향 없음)
- **이연**: blocking 차단 모드는 #64로 분리 (estimator delta 24.58% → #61 calibration 후 안전)

### #58: parse_json_response trailing characters tolerance (close, Slice 12 Step 0a)

- **history**:
  - Slice 11 Part 5: 신규 등록 (PS 1.0)
  - Slice 12 Step 0a: **close**
- **구현**: `portfolio/llm/parsers.py` Tier 3 raw_decode tolerance
  - Tier 1 ValidationError(json_invalid: trailing) 식별 → raw_decode 우회
  - backward-compat 100% (Tier 1/2 동작 무변경)
- **단위 테스트**: 6/6 PASS (trailing 3 패턴 + backward-compat 2 + invalid 1)
- **Slice 11 E3/haiku/#1 재현**: PASS

### #41: schema fitting trailing characters (close, Slice 12 Step 0a #58 dependency 해소)

- **history**:
  - Slice 11 Part 2: 본격 close → Part 3 유지 → Part 4/5 keep_open 1 part (V16 패턴)
  - Slice 12 Step 0a: **자연 close** (#58 보강으로 schema fitting 100% 회복)

### #59 (E3 본격 close): action_items measurability E3 (close, Slice 12 Step 0b)

- **history**:
  - Slice 11 Part 5: 신규 등록 (PS 1.5, E3 우선)
  - Slice 12 Step 0b: **E3 close** (4 케이스 micro-matrix NG 0%)
- **구현**: `E3PromptBuilder._E3_ACTION_RULES` 4종 규칙 명시
  - 구체성 필수 / 측정 가능성 필수 / 금지 패턴 / priority 정합성
- **단위 테스트**: 3/3 PASS
- **Micro-matrix**: 4/4 fitting PASS, NG 0% (baseline 50%)
- **비용**: $0.0554 (slice cap 5.54%)
- **잔여**: E5 25% NG는 Slice 13+ 후보로 §1에 등록

## §3. (이전) Slice 11 CLOSE 부채

### #48: token estimator v3 정착 (close, Slice 11 Part 4 N=26 견고화)

- **history**:
  - Slice 10 Step 0: v3 초안 도입 (estimator_v3.py + count_tokens API)
  - Slice 10 종결: count_tokens API 직접 호출로 ±2% 명세 활용 정착
  - Slice 11 Part 3 smoke: N=2 max_delta 0.0% 확인
  - **Slice 11 Part 4 매트릭스: N=24 max_delta 0.0% (누적 N=26)**
- **close 사유**: count_tokens API 명세 ±2%가 실측 N=26에서 **0% delta** — 완전 견고화. Slice 12+ 자연 활용.

### #52: raw messages 보존 정책 (close, Slice 11 Part 5 표기)

- Slice 11 Step 0 정착, Part 4 24 케이스 raw response 100% 보존 (`part4_matrix_dump.md`, `part4_matrix.json`).
- Part 5 24 케이스 평가 + Claude 비공개 평가 + merged 모두 보존 (`part5_*`).
- **close 확정**: messages 보존 hook + 정책 통합 완성.

### #41: schema fitting (Slice 11 Part 5에서도 keep_open 유지)

- **Part 5 처리**: keep_open 1 part 유지 (#58과 결합). #58 close 시점에 자연 close 예정.

> **수정 사항 vs Phase B 지시서 §5-2**: 지시서는 #41 "close" 처리를 권고했으나, V16 분석 결과 schema FAIL 원인이 parse_json_response 자체 한계(#58)로 식별됨. #58 close 전까지 #41은 keep_open 유지가 정직 — Slice 12에서 #58 close 즉시 #41 자연 close.

---

## §4. 부채 변화 요약 (Slice 13 Step 0a + 0b)

| 변화      | 건수 | 부채 ID                                                  |
| --------- | ---- | -------------------------------------------------------- |
| close     | 2    | #51 (fit 부분 close, Step 0a) / #62 (Step 0b)            |
| 신규 등록 | 4    | #61 (Slice 14), #63 (Slice 14+), #64 (Slice 14+), 추가 §1 등록 |
| 잔여      | 1    | #59 E5 (PS 0.5)                                          |
| **net**   | **+2** (close 2 − 신규 4)                                |

### 추적

- **Step 0a 신규**: #61 (3단 게이트 calibration, PS 2.5), #62 (estimator→CostGuard integration, PS 1.5), #63 (cost ledger 영속화, PS 1.5)
- **Step 0b 변동**: #62 → close (non-blocking 모드), #64 신규 (blocking 차단 모드 분리, PS 1.0)
- **#51**: Slice 11 Part 1 본격 → Slice 13 Step 0a에서 multivariate fit 정확도 개선 (fit 부분 close), integration은 #62로 분리됨

---

## §5. Slice 14+ 진입점 사전 등록

| 후보                                    | PS  | 우선순위        | 근거                                                                 |
| --------------------------------------- | --- | --------------- | -------------------------------------------------------------------- |
| #61 3단 게이트 경계값 calibration       | 2.5 | **Step 0 1순위** | 12 preset placeholder → 실측 분포 기반 fail/warn_below + manual eval |
| #59 E5 action measurability             | 0.5 | Step 0 2순위    | E5 25% NG, E3 패턴 재사용 가능                                       |
| #63 누적 비용 ledger 영속화             | 1.5 | Part 후보       | JSONL/SQLite ledger + slice flush                                    |
| #64 사전 추정 blocking 차단 모드        | 1.0 | Part 후보       | #61 calibration 완료 후 안전 (현재 estimator delta 24.58%)           |
| **#65 기존 순수 view 최종 처리 (E1~E6 마이그레이션 완료 후)** | **1.5** | **Slice 13 후반 Part** | E1~E6 DRF endpoint 전환 완료 시점에 유지/제거/wrapper화 결정 |

---

## §6. 부채 #26 분포 폭 (Slice 9~10 keep_open → Slice 11 close 확정)

- Slice 9 nat 폭 2 (self-eval bias 신호)
- Slice 11 Part 5: 병진 nat 폭 **3**, ins 폭 **3** (D2-A blind + rubric 가이드 효과)
- **#26 close 확정** (Slice 11 Part 5)
- Slice 12+ 매트릭스 슬라이스 manual eval은 D2-A blind 패턴 정착 적용
