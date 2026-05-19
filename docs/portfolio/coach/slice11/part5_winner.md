# Slice 11 Part 5 — Winner 판정 (D3-A)

**공식**: `final_score = 0.50 × efficiency + 0.25 × nat_mean + 0.25 × ins_mean`
**Efficiency 정규화**: `(baseline_cost / cost_ratio + baseline_latency / latency_ratio) / 2 × 5`, baseline = ($0.005, 10000ms), clamp [1.0, 5.0]
**Slice 9 호환**: 동일 공식 그대로 적용 (추세 비교)

---

## §1. 자동 측정값 (Part 4 matrix.json, n=12 per model)

| model  | cost_avg     | latency_avg | efficiency_score |
| ------ | ------------ | ----------- | ---------------- |
| haiku  | **$0.00472** | **8601ms**  | **5.000** (clamp) |
| sonnet | $0.01510     | 15885ms     | 2.402            |

- haiku는 baseline 양쪽 모두 우위 → efficiency 만점
- sonnet은 cost 3.2× 비싸고 latency 1.85× 느림 → efficiency 2.4

---

## §2. 평가자별 winner 계산

| 평가자     | 모델   | nat_mean | ins_mean | actn OK | efficiency | **final_score** | winner    |
| ---------- | ------ | -------- | -------- | ------- | ---------- | --------------- | --------- |
| **병진**   | haiku  | 3.583    | 3.750    | 5/6     | 5.000      | **4.333**       | ← winner  |
| **병진**   | sonnet | 3.083    | 3.417    | 4/6     | 2.402      | 2.826           |           |
| **Claude** | haiku  | 4.000    | 4.000    | 4/6     | 5.000      | **4.500**       | ← winner  |
| **Claude** | sonnet | 4.833    | 4.250    | 5/6     | 2.402      | 3.472           |           |

### 핵심 발견 (Two-level analysis)

**Level 1 — 정성 평균만 비교 (efficiency 무시)**:
- 병진: haiku nat 3.583 > sonnet 3.083 (+0.5), haiku ins 3.750 > 3.417 (+0.33) → **병진 haiku 우위**
- Claude: sonnet nat 4.833 > haiku 4.0 (+0.83), sonnet ins 4.25 > 4.0 (+0.25) → **Claude sonnet 우위**
- 두 평가자 **정성 축에서 정반대 결론**

**Level 2 — D3-A 공식 (efficiency 50% 가중)**:
- 병진: haiku 4.333 > sonnet 2.826 (격차 +1.507) → **haiku 압승**
- Claude: haiku 4.500 > sonnet 3.472 (격차 +1.028) → **haiku 우위**
- 두 평가자 **D3-A 적용 시 winner 일치**

---

## §3. 두 평가자 일치/불일치

- **병진 winner**: **haiku** (final_score 4.333)
- **Claude winner**: **haiku** (final_score 4.500)
- **일치 여부**: **O (일치)** — D3-A 공식 적용 시
- 정성 평균만 보면 Claude는 sonnet 쪽 — **anchor bias 회피 정당성은 정성 축에서 명확**

---

## §4. Ground truth 판정

**최종 winner**: **haiku** (D3-A 공식 기준, 양 평가자 일치)

### haiku 우위 정량 (병진 ground truth)
- 품질:
  - naturalness: 3.583 vs sonnet 3.083 (**+0.5**)
  - insight: 3.750 vs sonnet 3.417 (**+0.33**)
  - actionability: 5/6 (83%) vs sonnet 4/6 (67%) (**+17%p**)
- Efficiency (Part 4 매트릭스):
  - cost: $0.00472 vs $0.01510 (**3.2× cheaper**)
  - latency: 8.6s vs 15.9s (**1.85× faster**)
  - efficiency_score: 5.0 vs 2.4 (격차 +2.6)
- final_score 격차: **+1.507** (병진 ground truth)

### Double win (품질 + efficiency 모두 haiku)
병진 ground truth 기준으로 모든 축에서 haiku 우위. efficiency가 50% 가중이므로 Claude 평가에서도 동일 결론으로 수렴.

---

## §5. 글쓰기 가설 7/7 확정

D2.B "글쓰기 차원 = haiku" 가설 — Slice 1·3·4·5·6·7·8·11에서 일관 외삽:

| 슬라이스 | 진입점         | winner    |
| -------- | -------------- | --------- |
| 1        | E1+GARP        | haiku     |
| 3        | E2 4요소       | haiku     |
| 4        | E6 비교        | haiku     |
| 5        | E3 metric      | haiku     |
| 6        | E3 portfolio   | haiku     |
| 7        | E4 대화        | haiku     |
| 8        | E5 trio        | haiku     |
| **11**   | **6 진입점 통합** | **haiku** |

**D2.B 외삽 완전 확정**. production default provider = `"haiku"` 유지.
