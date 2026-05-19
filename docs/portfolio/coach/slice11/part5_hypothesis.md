# Slice 11 Part 5 — Hypothesis + Inter-Rater Agreement (D1-D 첫 적용)

**작성일**: 2026-05-19
**Rubric**: D1-D 3축 하이브리드 (naturalness 1~5 / insight 1~5 / actionability OK·NG·N/A)
**평가자 A (ground truth)**: 병진 (한국어 native)
**평가자 B (사후 보조)**: claude-opus-4-7

---

## §1. Inter-rater Agreement

| 축                                | 완전 일치 % | ±1 이내 일치 % |
| --------------------------------- | ----------- | -------------- |
| naturalness                       | **25.0%**   | **58.3%**      |
| insight                           | **20.8%**   | **79.2%**      |
| actionability (E1/E3/E5만, n=12)  | **83.3%**   | -              |

### 해석
- **정성 축 (nat/ins) 완전 일치율 21~25%**: 인간 vs LLM 평가의 자연 격차 (1~5 척도에서 0.5점 단위 미세 판단 차이 누적)
- **±1 일치율 58~79%**: 큰 그림은 같으나 미세 차이 존재 — rubric 견고성은 양호
- **actionability 83%**: 객관 기준(OK/NG)이라 일치율 높음 — 정성보다 객관 축이 평가자 합의 강함
- Slice 12+ 매트릭스 슬라이스 manual eval에서 동일 패턴 재현 가능

---

## §2. 분포 폭 측정 (#26 후처리)

| 평가자 | 축          | min | max | **폭** | mean  | 판정                  |
| ------ | ----------- | --- | --- | ------ | ----- | --------------------- |
| 병진   | naturalness | 2   | 5   | **3**  | 3.333 | **#26 close 후보**    |
| 병진   | insight     | 2   | 5   | **3**  | 3.583 | **#26 close 후보**    |
| Claude | naturalness | 3   | 5   | 2      | 4.417 | (참고용, anchor 모델) |
| Claude | insight     | 3   | 5   | 2      | 4.125 | (참고용)              |

### #26 판정 (병진 ground truth 기준)
- 폭 ≥ 3 → **#26 close 후보** (D2-A blind + rubric "양극단 활용" 가이드 효과 입증)
- Slice 9 폭 2 → **Slice 11 폭 3 개선** (rubric 가이드 + blind 분리 평가 효과)
- **#26 close 확정** (Step 8에서 처리)

### Claude는 박하게 평가 못함
- 모든 케이스를 3~5점 사이로 집중 (폭 2)
- 모델 자체의 점수 매김 편향 — 인간 평가자만큼 박한 판단 어려움
- → Claude는 사후 검증/모니터링용으로만 활용, **ground truth는 병진**

---

## §3. 글쓰기 가설 (8슬라이스 누적)

| 슬라이스 | 진입점            | winner    | 누적        |
| -------- | ----------------- | --------- | ----------- |
| S1       | E1+GARP           | haiku     | 1/1         |
| S3       | E2                | haiku     | 2/2         |
| S4       | E6                | haiku     | 3/3         |
| S5       | E3                | haiku     | 4/4         |
| S6       | concentrated E3   | haiku     | 5/5         |
| S7       | E4 대화           | haiku     | 6/6         |
| S8       | E5 trio           | haiku     | 7/7 잠정    |
| **S11**  | **6 진입점 통합** | **haiku** | **7/7 확정** |

**D2.B "글쓰기 차원 = haiku" 가설 — 일관 외삽 완전 확정**.
- production default provider = `"haiku"` 유지 정당화
- Slice 12+ 새 진입점 추가 시에도 default haiku 가설 외삽 적용

---

## §4. Actionability NG 비율 (병진 ground truth, D1-D 모니터링 첫 적용)

| entry    | OK         | NG         | NG ratio | 판정              |
| -------- | ---------- | ---------- | -------- | ----------------- |
| E1       | **4/4**    | 0/4        | **0.0%** | 양호              |
| E3       | 2/4        | **2/4**    | **50.0%**| **즉시 보강 필요** |
| E5       | 3/4        | 1/4        | **25.0%**| prompt 보강 후보  |
| **종합** | **9/12**   | **3/12**   | **25.0%**| 보강 후보         |

### Slice 12+ 운영 기준 적용
- NG ratio < 10%: 양호 (E1만 해당)
- NG ratio 10~30%: prompt 보강 후보 (E5, 종합)
- NG ratio > 30%: **즉시 prompt 보강** (E3 50%)

### E3 NG 50% 패턴 분석 (병진 평가 노트 + 사후 비교)
NG 케이스: V9 (e3 haiku #2), V24 (e3 sonnet #2)
- 공통 패턴: "재평가/검토" 다수, 수치 목표 명시 없음
- "5~10% 비중 조정" 같이 정량 인용해도 명확한 목표 수치 부족
- Claude 평가에서는 V24를 OK로 판정 (불일치) — 한국어 사용자가 더 박하게 판단

**#59 신규 등록 정당화**: E3 50% NG는 prompt에 "수치 목표 또는 기한 명시 강제" 룰 도입 즉시 필요. Slice 12 Step 0 후보로 PS 1.5 등록.

---

## §5. Anchor Bias 회피 효과 (D2-A 입증)

### 정성 축 정반대 결론
- 병진: haiku 우위 (nat +0.5, ins +0.33)
- Claude: sonnet 우위 (nat +0.83, ins +0.25)
- 두 평가자 **정성 평균 직접 비교 시 winner 정반대**

### D3-A 가중치 적용 시 수렴
- efficiency 50% 비중이 결정적 (haiku 5.0 vs sonnet 2.4)
- 양 평가자 모두 D3-A final_score 기준 **haiku winner 일치**

### Anchor bias 회피 정당성
- **만약 Claude 점수를 anchor로 노출했다면**: 병진 정성 평가도 sonnet 쪽으로 기울 위험
- → ground truth 왜곡 → D3-A 점수도 sonnet 쪽으로 이동 가능
- **blind 분리 평가가 ground truth 보존**

### Slice 12+ 매트릭스 슬라이스 manual eval 패턴 정착 후보
1. **D2-A blind shuffle** (seed=42, `scripts/manual_eval_shuffle.py`)
2. **사후 비교 dump** (Claude 평가 비공개, 병진 평가 완료 후 공개)
3. **D3-A 가중치 공식** (eff 50% + nat 25% + ins 25%)
4. **inter-rater agreement 측정** (rubric 견고성 자체 검증)
5. **Actionability NG ratio 모니터링** (prompt 보강 자동 식별)

→ Slice 12+ 매트릭스 슬라이스 표준 패턴 등록.
