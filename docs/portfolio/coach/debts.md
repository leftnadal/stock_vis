# Portfolio Coach 부채 대장 (Slice 12 Step 0 종결 기준)

**최종 갱신**: 2026-05-20 (Slice 12 Step 0 multi-debt mini-slice)
**관리 원칙**: 매 슬라이스 종결 시 갱신. close/keep_open/신규 변동 명시.

---

## §1. 현재 OPEN 부채

### #51: output_token estimator multivariate / GAM (PS 1.5)

- **history**:
  - Slice 11 Part 1: 본격 구현 (8 진입점 char ratio 단변량 fit)
  - 진입점 기준 max_delta 33.12%, P90 11.20%, mean 5.11%
- **현재 상태**: open, **Slice 12 Step 0 1순위 후보**
- **목표**: Part 4 24 케이스 output_tokens 데이터 누적 활용 → multivariate fit 또는 GAM
- **데이터 가용성**: haiku 평균 917 tokens, sonnet 743 tokens, 진입점 × 모델 × 반복 데이터 풀

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

## §2. 이번 슬라이스 (Slice 12 Step 0) CLOSE 부채

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

## §4. 부채 변화 요약 (Slice 12 Step 0 multi-debt mini-slice)

| 변화      | 건수 | 부채 ID                                          |
| --------- | ---- | ------------------------------------------------ |
| close     | 3    | #58, #41 (dep), #59 E3                           |
| 신규 등록 | 0    | -                                                |
| 잔여      | 2    | #51 (PS 1.5), #59 E5 (PS 0.5)                    |
| **net**   | **−3** (close 3 − 신규 0)                        |

> **multi-debt mini-slice 첫 사례**: Slice 10 single-debt mini + Slice 11 multi-debt 융합 패턴 정착.

---

## §5. Slice 13+ 진입점 사전 등록

| 후보                                    | PS  | 우선순위           | 근거                                                 |
| --------------------------------------- | --- | ------------------ | ---------------------------------------------------- |
| #51 output_token multivariate estimator | 1.5 | **Step 0 1순위**   | Slice 11 Part 4 + Slice 12 Step 0b 데이터 누적     |
| #59 E5 action measurability             | 0.5 | Step 0 2순위 (저 PS) | E5 25% NG, E3 패턴 재사용 가능                     |

---

## §6. 부채 #26 분포 폭 (Slice 9~10 keep_open → Slice 11 close 확정)

- Slice 9 nat 폭 2 (self-eval bias 신호)
- Slice 11 Part 5: 병진 nat 폭 **3**, ins 폭 **3** (D2-A blind + rubric 가이드 효과)
- **#26 close 확정** (Slice 11 Part 5)
- Slice 12+ 매트릭스 슬라이스 manual eval은 D2-A blind 패턴 정착 적용
