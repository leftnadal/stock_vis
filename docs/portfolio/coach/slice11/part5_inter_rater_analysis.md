# Slice 11 Part 5 — Inter-rater Analysis + Winner 확정

**작성일**: 2026-05-19
**평가자 A**: 병진 (단일 평가자, blind, ground truth)
**평가자 B**: claude-opus-4-7 (사후 비교용 보조)
**Rubric**: D1-D 3축 하이브리드 (naturalness 1~5 / insight 1~5 / actionability OK·NG·N/A)

---

## §1. 병진 평가 분포 (24 cases)

### naturalness
| 점수 | 건수 |
| ---- | ---- |
| 5    | 1    |
| 4    | 9    |
| 3    | 11   |
| 2    | 3    |
| 1    | 0    |

- **min=2, max=5, 폭=3** (Slice 11 KPI ≥3 **PASS**, Slice 9 폭 2 대비 개선)
- 평균: **3.333**

### insight
| 점수 | 건수 |
| ---- | ---- |
| 5    | 4    |
| 4    | 8    |
| 3    | 10   |
| 2    | 2    |
| 1    | 0    |

- **min=2, max=5, 폭=3 PASS**
- 평균: **3.583**

### actionability (EVAL 12건 = E1/E3/E5)
- OK: 9건 (75%)
- NG: 3건 (25%)
- N/A: 12건 (E2/E4/E6)

---

## §2. 모델별 평균 (병진 평가, 6 EVAL haiku + 6 EVAL sonnet)

| 항목                       | haiku (n=12)  | sonnet (n=12) | sonnet − haiku |
| -------------------------- | ------------- | ------------- | -------------- |
| naturalness 평균           | **3.583**     | 3.083         | **−0.500**     |
| insight 평균               | **3.750**     | 3.417         | **−0.333**     |
| actionability OK rate      | **5/6 (83%)** | 4/6 (67%)     | **−17%p**      |

### 병진 평가 winner: **haiku 압승**
- naturalness +0.5 (sonnet보다 한국어 더 자연)
- insight +0.33 (sonnet보다 통찰력 우위)
- actionability +17%p (구체성·측정가능성 우위)

---

## §3. Inter-rater Agreement (병진 vs Claude)

### naturalness
- 동의(=0): **6/24** (25%)
- ±1 격차: 8건
- ±2 격차: 8건
- ±3 격차: 2건 (V6, V8 — sonnet 케이스, Claude 5점 vs 병진 2점)
- 평균 격차: **−1.083** (병진이 Claude보다 1.08점 박함)

### insight
- 동의(=0): **5/24** (21%)
- ±1 격차: 14건 (가장 흔한 패턴)
- ±2 격차: 4건
- ±3 격차: 1건 (V14 — 병진 2 vs Claude 5)
- 평균 격차: **−0.542**

### actionability (EVAL 12건)
- 일치: **10/12 (83%)**
- 불일치 2건:
  - V18 (e5 haiku #1): 병진 OK / Claude NG (병진 측 측정가능성 인정)
  - V24 (e3 sonnet #2): 병진 NG / Claude OK (병진 측 구체성 미흡 판단)

---

## §4. 두 평가자 winner 결론 — **정반대**

| 평가자  | naturalness winner | insight winner | actionability winner | 종합 winner |
| ------- | ------------------ | -------------- | -------------------- | ----------- |
| 병진    | **haiku** +0.5     | **haiku** +0.33| **haiku** +17%p      | **haiku**   |
| Claude  | sonnet +0.83       | sonnet +0.25   | 동률 5/6             | sonnet      |

### 해석
- Claude는 sonnet의 더 길고 정성적인 표현을 5점으로 평가
- 병진(한국어 native)은 같은 응답을 더 박하게 평가 — **anchor 없이 진짜 한국어 사용자 관점**
- Claude 평가가 시스템적으로 sonnet 편향 (모델이 같은 패밀리 응답을 좋게 보는 경향)
- **anchor bias 회피 정책 (D2-A blind) 정당화**: 만약 Claude 점수를 anchor로 노출했다면 병진도 sonnet 쪽으로 기울었을 위험

### Ground Truth
- **병진 평가가 ground truth** — 한국어 사용자, 실제 서비스 사용자 입장
- Claude 평가는 inter-rater 신호로만 활용

---

## §5. Slice 11 winner 최종 확정: **haiku**

### 품질 (병진 평가)
- naturalness 3.583 vs sonnet 3.083 (+0.5)
- insight 3.750 vs sonnet 3.417 (+0.33)
- actionability 5/6 vs sonnet 4/6 (+17%p)

### Efficiency (Part 4 매트릭스 실측)
- cost: $0.00472 vs sonnet $0.01510 (**3.2× cheaper**)
- latency: 8.6s vs sonnet 15.9s (**1.85× faster**)

### 종합: **Double win** (품질 + efficiency 모두 haiku 우위)
- D2.B "글쓰기 차원 = haiku" 가설 **7/7 확정** (Slice 1·3·4·5·6·7·8·11에서 모두 haiku 우위 또는 동급 cost 절감)
- E2.B 외삽 (Slice 9 이후 추가 검증) **PASS**
- production default provider = haiku 유지

---

## §6. 특이 케이스 분석

### V16 — e3 haiku #1 (schema FAIL, 병진 3/3/OK)
- Part 4 매트릭스 1건 fitting FAIL (95.83% PASS rate)
- 병진 평가 nat=3, ins=3, actn=OK — content는 보통 수준이지만 actionability는 합격
- Claude 평가 nat=5, ins=5, actn=OK — content 우수 판정 (불일치)
- **공통 진단**: actionability는 OK (정량 명시 우수), schema FAIL은 별개 문제
- **#41 keep_open 처리**: prompt가 JSON-only 강제했음에도 haiku가 JSON 뒤 markdown 텍스트 첨부
- **#58 후보 강화**: `parse_json_response` trailing tolerance 도입 검토 (PS 1.0)

### V8 — e6 sonnet #1 (병진 nat=2, ins=2 / Claude 5/4)
- 최대 격차 케이스 (nat −3, ins −2)
- 응답 자체는 자연하나 병진이 매우 박하게 평가
- 가설: VZ yield trap 동일 패턴 반복 (V4 sonnet, V8 sonnet, V2 haiku 모두 유사 표현)
- → 병진이 반복 패턴 감지 → 박한 점수
- **시사점**: 24 케이스 반복 평가 시 패턴 피로도 발생 — Slice 12+ rubric에 "반복 표현 페널티" 명시 후보

### NG 3건 (병진)
- V9 (e3 haiku #2): 정량 수치 목표 명시 없음
- V17 (e5 sonnet #2): DRIP/모니터링 추상적
- V24 (e3 sonnet #2): Claude는 OK 판정 (불일치)

→ 공통: action_items의 measurability 약함. **#59 후보**: Slice 12+ prompt에 "수치 목표 또는 기한 명시 강제" 추가.

---

## §7. Phase B 처리 부채 매핑

| 부채 ID | Phase B 처리 결과                                       |
| ------- | ------------------------------------------------------- |
| #41     | **keep_open 1 part 유지** — V16 패턴 분석 완료, Slice 12+ #58 결합 |
| #48     | **CLOSE 확정** (Part 4 견고화 PASS)                     |
| #51     | 유지 (Slice 12+ Step 0 후보)                            |
| #52     | close 유지                                              |
| #57 (후보) | **확정 등록** — KPI 10 임계 보정 (매트릭스 슬라이스 +10~15) |
| #58 (후보) | **확정 등록** — parse_json_response trailing tolerance (PS 1.0) |
| #59 (신규 후보) | action_items measurability prompt 강화 (PS 1.5)    |
