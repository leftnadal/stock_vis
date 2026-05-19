# Portfolio Coach 부채 대장 (Slice 11 종결 기준)

**최종 갱신**: 2026-05-19 (Slice 11 Part 5 Phase B)
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

### #41: schema fitting trailing characters (keep_open 1 part)

- **history**:
  - Slice 11 Part 2: 본격 close (4 조건 통과)
  - Slice 11 Part 3: close 유지 (smoke 2/2 fitting PASS)
  - Slice 11 Part 4: keep_open 1 part (24 케이스 매트릭스 1/24 FAIL — e3/haiku/#1)
  - Slice 11 Part 5: **keep_open 유지** (V16 패턴 분석 완료, #58과 결합)
- **재현 빈도**: 4.17% (1/24)
- **패턴**: LLM 응답이 valid JSON 뒤에 `---\n\n## 추가 코멘트\n...` 형식 마크다운 덧붙임
- **처리 방향**: parse_json_response 보강 (#58)으로 흡수 가능

### #58: parse_json_response trailing characters tolerance (신규, PS 1.0)

- **발견**: Slice 11 Part 4 (e3/haiku/#1) + Part 5 V16 분석에서 강화
- **재현 빈도**: 4.17% (1/24)
- **패턴**: LLM 응답이 valid JSON 뒤에 markdown 텍스트 덧붙임
- **현재 처리**: ValidationError (json_invalid: trailing characters)
- **목표**: 첫 valid JSON 블록만 추출하여 fitting 통과 (tolerance 도입)
- **Slice 12 Step 0 2순위**: 검토 → 적용
- **테스트 케이스 후보**: trailing markdown / trailing JSON / trailing 빈 객체 3 패턴
- **작업 추정**: ~30~45분 (regex 보강 + 단위 테스트 3~5건)

### #59: action_items measurability prompt 강화 (신규, PS 1.5)

- **발견**: Slice 11 Part 5 D1-D actionability 평가
- **발생률**: E3 50% NG (2/4), E5 25% NG (1/4), E1 0% NG, **종합 25% NG**
- **패턴**: action_items의 description이 "재평가/검토/모니터링" 등 추상적 표현
- **목표**: prompt에 "수치 목표 또는 기한 명시 강제" 룰 도입 (E3 진입점 우선)
- **Slice 12 Step 0 3순위**: prompt 보강 (E3 우선, E5 차순)
- **NG 임계 기준**:
  - NG ratio < 10%: 양호
  - 10~30%: 보강 후보
  - **> 30%: 즉시 보강** (E3 해당)

### #57: KPI 임계 보정 (close, Slice 11 Part 5 D5-A 적용)

- Slice 11 Part 5에서 **close**. KPI spec 갱신 완료 (`kpi_matrix.md`).
- 슬라이스 유형별 회귀 +Δ 임계 (매트릭스 슬라이스 +10~15, manual eval +2~5).

---

## §2. 이번 슬라이스 (Slice 11) CLOSE 부채

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

## §3. 부채 변화 요약 (Slice 11 전체)

| 변화      | 건수 | 부채 ID          |
| --------- | ---- | ---------------- |
| close     | 3    | #48, #52, #57    |
| 신규 등록 | 2    | #58 (PS 1.0), #59 (PS 1.5) |
| 유지      | 2    | #51, #41 (keep_open 1 part) |
| **net**   | **−1** (close 3 − 신규 2) |

---

## §4. Slice 12 진입점 사전 등록

| 후보                                    | PS  | 우선순위           | 근거                                                 |
| --------------------------------------- | --- | ------------------ | ---------------------------------------------------- |
| #51 output_token multivariate estimator | 1.5 | **Step 0 1순위**   | Part 4 24 케이스 데이터 누적 → multivariate 가능    |
| #58 parse trailing tolerance            | 1.0 | **Step 0 2순위**   | 4.17% FAIL 즉시 해소, #41 자연 close                |
| #59 action measurability (E3 우선)      | 1.5 | **Step 0 3순위**   | E3 50% NG 즉시 보강                                  |

---

## §5. 부채 #26 분포 폭 (Slice 9~10 keep_open → Slice 11 close 확정)

- Slice 9 nat 폭 2 (self-eval bias 신호)
- Slice 11 Part 5: 병진 nat 폭 **3**, ins 폭 **3** (D2-A blind + rubric 가이드 효과)
- **#26 close 확정** (Slice 11 Part 5)
- Slice 12+ 매트릭스 슬라이스 manual eval은 D2-A blind 패턴 정착 적용
