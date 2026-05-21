# Portfolio Coach 부채 대장 (Slice 13 + #65 종결)

**최종 갱신**: 2026-05-22 (#65 closing — legacy view 처리 마감, #67 신규)
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

### #66: E3 endpoint preset 점수 기능 API 노출 (분석엔진 #12 Phase 2 후, PS 2.0)

- **신규 등록**: Slice 13 Part 3 (2026-05-21)
- **요지**: `run_e3_coach`의 `preset_id` + `metrics` kwarg를 E3 endpoint 요청 표면에
  **optional 필드로 노출** → ScoringEngine 점수 기반 진단(가중합/gate_tier) 제공
- **현재 상태 (Part 3 v2)**: kwarg는 endpoint에 미노출 — `run_e3_coach` 기본값(None) 사용
- **선행조건**: **분석엔진 #12 (Phase 2)** 완성
  - 7종 정규화 지표 중 3종 (`sector_hhi`, `portfolio_beta`, `avg_correlation`)이
    외부 데이터(수익률 시계열·섹터 라벨)에 의존 → 분석엔진 없이는 서버·클라이언트
    모두 산출 불가. ScoringEngine은 7종 완비를 전제.
- **작업 범위 (분석엔진 #12 후)**:
  - E3 endpoint에 `preset_id: Optional[str]` + `metrics: Optional[dict]` ADDITIVE 추가
  - `metrics`는 클라이언트가 보내거나 서버가 분석엔진 호출로 계산 (옵션 결정 필요)
  - ScoringEngine.score() 결과(scores, gate_tier)를 응답에 포함
- **breaking change 여부**: ADDITIVE → 기존 E3 클라이언트 무손상
- **PS**: 2.0 (Phase 2 블록)
- **참조**: `portfolio/services/coach/e3_service.py:34` (kwarg 시그니처),
  `portfolio/services/scoring/PRESET_ID_TO_CATEGORY` (12 preset 진실 소스)

### #67: legacy 전용 의존 코드 후속 정리 (Slice 14+, PS 1.0)

- **신규 등록**: #65 closing (2026-05-22)
- **성격**: 비위험·개선성 부채. 보존된 코드는 검증 스크립트가 실제로 쓰는
  live code이므로 dead code가 아니며, 방치해도 깨지지 않음.
- **배경**: #65에서 legacy view 5건 제거 시, 그 view들이 쓰던 옛 보조 코드는
  `scripts/validation/` 및 `test_e*_service.py`, `schemas/__init__.py:__all__`에
  아직 쓰여 보존됨. 본 부채는 그 보존 코드의 정리 검토.
- **제안 방향**:
  1. `scripts/validation/`을 archived/legacy로 분류 (슬라이스 1~6 검증용 — 운영 무관)
  2. archive 후 legacy 의존 코드 일괄 제거 검토
  3. `services/__init__.py:__all__` 정리

#### 누적 보존 목록 (E5/E6 회신 첨부 — 재조사 비용 절감)

**Service 함수 (5건, services/__init__.py __all__ 또는 test_*_service.py 의존)**:
| 함수 | 파일 | 보존 사유 |
|------|------|----------|
| `run_e1_garp` | `services/e1_garp.py` | `services/__init__.py:__all__` 노출 |
| `run_e2` | `services/e2_diagnostic_card.py` | `test_e2_service.py` 직접 import |
| `run_e3` | `services/e3_metric_comment.py` | `test_e3_service.py` 직접 import |
| `run_e5` | `services/e5_adjustment_parser.py` | `__all__` + `test_e5_service.py` |
| `run_e6` | `services/e6_comparison.py` | `test_e6_service.py` 직접 import |

**Prompt builders (5건, 주로 scripts/validation/)**:
| 함수 | 사용처 |
|------|--------|
| `build_e1_prompt` | `scripts/validation/` 5건 + `test_scenario_e2e.py` |
| `build_e2_prompt` | `scripts/validation/` 3건 + `test_e2_service.py` |
| `build_e3_prompt` | `scripts/validation/` 3건 |
| `build_e5_prompt` | `scripts/validation/` 3건 + `test_e5_service.py` |
| `build_e6_prompt` | `scripts/validation/` 3건 + `test_scenario_e2e.py` |

**Parsers (3건)**:
| 함수 | 사용처 |
|------|--------|
| `parse_e2_response` | `scripts/validation/` 2건 + `test_e2_service.py` |
| `parse_e3_response` | `scripts/validation/` 2건 |
| `parse_e6_response` | `scripts/validation/` 2건 |

**Schemas**:
| 스키마 | 사용처 |
|--------|--------|
| `OneLineDiagnosis` (E1) | `scripts/validation/` 5건 + `parsers.py` docstring |
| `E2Request`, `E2Response`, `E2DiagnosticCard` | `scripts/validation/` 3건 + `test_e2_*` 다수 + `schemas/__init__.py:__all__` |
| `E3Request` | `scripts/validation/` 3건 |
| `E5Request`, `E5Response` | `scripts/validation/` 3건 + `test_e5_service.py` |
| `E6Request` | `scripts/validation/` 3건 |

**공통 패턴**: `scripts/validation/`(슬라이스 1~6 검증 스크립트 — 역사 보존)이 가장 큰
보존 사유. 차선은 `test_e*_service.py`(service 단위 테스트). `schemas/__init__.py:__all__`
노출은 외부 import 가능성 신호.

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

## §2. 최근 슬라이스 CLOSE 부채 (Slice 12 Step 0 + Slice 13 Step 0a/0b/Part 1 + #65)

### #65: 기존 순수 Django view 최종 처리 (close, #65 mini-slice 2026-05-21~22)

- **history**:
  - Slice 13 Part 1: 신규 등록 (legacy 5건 + E4 부재 special case)
  - Slice 13 종결 후 #65 mini-slice로 처리 시작
  - 당초 wrapper 추천 → E1 pilot에서 재평가 → **제거**로 전환
- **처리 결과**: E1~E3·E5·E6 legacy view 전수 제거 (경로 A 일관 = 호출처 0건 dead code)
- **commit**: E1 `4eba9fb` / E2 `fc39d23` / E3 `3e3ad6b` / E5 `2bde79e` / E6 `1983a99` / doc `4c2fcc9`
- **검증**: 회귀 767→730 (−37 = 5+7+9+7+9 정확) / IDENTICAL 31/31 / 6 API 60/60 PASS / $0
- **결과**: 6 진입점 모두 `/api/v1/coach/eN/` 단일화 (이중 입구 소멸)
- **잔여**: legacy 전용 의존 코드(scripts/validation/, test_e*_service.py 사용중) → **#67로 분리 등록**

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

## §4. 부채 변화 요약 (Slice 13 Step 0a + 0b + Part 1~5 + #65)

| 변화      | 건수 | 부채 ID                                                  |
| --------- | ---- | -------------------------------------------------------- |
| close     | 3    | #51 (fit, Step 0a) / #62 (Step 0b) / **#65 (closing)**   |
| 신규 등록 | 6    | #61, #63, #64 (Step 0a/0b) / #65 (Part 1) → close / #66 (Part 3) / **#67 (closing)** |
| 잔여      | 1    | #59 E5 (PS 0.5)                                          |
| **net**   | **+3** (close 3 − 신규 6)                                |

### 추적

- **Step 0a 신규**: #61 (3단 게이트 calibration, PS 2.5), #62 (estimator→CostGuard integration, PS 1.5), #63 (cost ledger 영속화, PS 1.5)
- **Step 0b 변동**: #62 → close (non-blocking 모드), #64 신규 (blocking 차단 모드 분리, PS 1.0)
- **Part 1 신규**: #65 (legacy view 최종 처리, PS 1.5) — 등록 시점 wrapper/유지 우선 권고
- **Part 3 신규**: #66 (E3 preset 점수 API, PS 2.0, 분석엔진 #12 Phase 2 의존)
- **#65 closing**: legacy view 5건 제거(경로 A) → close. **#67 신규** (legacy 보조 코드 정리, PS 1.0)
- **#51**: Slice 11 Part 1 본격 → Step 0a에서 multivariate fit 정확도 개선 (fit 부분 close), integration은 #62로 분리됨

---

## §5. Slice 14+ 진입점 사전 등록

| 후보                                    | PS  | 우선순위        | 근거                                                                 |
| --------------------------------------- | --- | --------------- | -------------------------------------------------------------------- |
| #61 3단 게이트 경계값 calibration       | 2.5 | **Step 0 1순위** | 12 preset placeholder → 실측 분포 기반 fail/warn_below + manual eval |
| #59 E5 action measurability             | 0.5 | Step 0 2순위    | E5 25% NG, E3 패턴 재사용 가능                                       |
| #63 누적 비용 ledger 영속화             | 1.5 | Part 후보       | JSONL/SQLite ledger + slice flush                                    |
| #64 사전 추정 blocking 차단 모드        | 1.0 | Part 후보       | #61 calibration 완료 후 안전 (현재 estimator delta 24.58%)           |
| **#66 E3 endpoint preset 점수 API 노출** | **2.0** | **분석엔진 #12 Phase 2 후** | preset_id+metrics optional 필드 ADDITIVE 추가. 분석엔진 선행 필요 |
| **#67 legacy 전용 의존 코드 후속 정리** | **1.0** | Part 후보 (비위험) | scripts/validation/ archive 우선 → 보조 코드 일괄 제거 검토. 누적 보존 목록 §1 첨부 |

---

## §6. 부채 #26 분포 폭 (Slice 9~10 keep_open → Slice 11 close 확정)

- Slice 9 nat 폭 2 (self-eval bias 신호)
- Slice 11 Part 5: 병진 nat 폭 **3**, ins 폭 **3** (D2-A blind + rubric 가이드 효과)
- **#26 close 확정** (Slice 11 Part 5)
- Slice 12+ 매트릭스 슬라이스 manual eval은 D2-A blind 패턴 정착 적용
