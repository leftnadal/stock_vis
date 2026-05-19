# Slice 11 Part 5 — Claude 사후 비교 평가 (비공개)

**평가자**: claude-opus-4-7
**평가일**: 2026-05-19
**Rubric**: `manual_eval_rubric.md` (D1-D 3축 하이브리드)
**목적**: 병진 blind 평가 완료 후 Phase B에서 inter-rater 분석 보조 지표
**원칙**: 병진 평가 완료까지 본 파일 비공개 — anchor bias 회피

---

## §1. View별 평가 (24 케이스, view_idx 순)

| View # | entry | model  | rep | nat | ins | actn | note |
| ------ | ----- | ------ | --- | --- | --- | ---- | ---- |
| 1      | e4    | haiku  | 2   | 4   | 4   | N/A  | 배당귀족 + 방어섹터 + ETF 분산 + 트레이드오프 균형 양호 |
| 2      | e6    | haiku  | 1   | 3   | 4   | N/A  | VZ 6.8을 '70점대'로 표현 혼동 (0~10 vs 100점 척도 혼용) |
| 3      | e1    | sonnet | 2   | 5   | 5   | OK   | PEG 80% 미달 + 종목별 정량 + 재배분 비중 명시 (4/4) |
| 4      | e6    | sonnet | 2   | 5   | 4   | N/A  | 구체적 score 인용 + 약점 명시, 다소 데이터 나열적 |
| 5      | e2    | haiku  | 2   | 4   | 3   | N/A  | 데이터 나열 + 일부 의미 부여 (완충 역할) |
| 6      | e5    | sonnet | 1   | 5   | 5   | OK   | 분기당 +2.5bp 평균 + 가속도 + 베타 + expense ratio 가중평균 (3/4) |
| 7      | e6    | haiku  | 2   | 4   | 4   | N/A  | VZ 약점 분석 양호, View #2와 유사 |
| 8      | e6    | sonnet | 1   | 5   | 4   | N/A  | 구체 score + 약점 + 섹터 단일 종목 집중 |
| 9      | e3    | haiku  | 2   | 4   | 4   | NG   | '재평가/검토' 다수, 수치 목표 명시 없음 (2.5/4) |
| 10     | e5    | haiku  | 2   | 4   | 4   | OK   | borderline 3/4 — KO+PEP+VYM 인용 OK |
| 11     | e2    | haiku  | 1   | 4   | 3   | N/A  | 데이터 나열 위주, ETF 수익률 비교 1건 |
| 12     | e1    | haiku  | 2   | 4   | 5   | OK   | 종목별 정량 + 재배분 비중 4건 명시 (4/4) |
| 13     | e4    | sonnet | 2   | 5   | 4   | N/A  | 배당 안정성 질문에 정확 답변, 배당귀족주 이력 인용 |
| 14     | e1    | sonnet | 1   | 4   | 5   | OK   | PEG 분석 + VZ 20→10% 명시 (4/4) |
| 15     | e4    | sonnet | 1   | 5   | 4   | N/A  | 배당귀족주 + 섹터 + VZ 통신 경쟁 |
| 16     | e3    | haiku  | 1   | 5   | 5   | OK   | schema FAIL이지만 content 풍부 — HHI + ETF 간접 편중 + 정량 (4/4) |
| 17     | e5    | sonnet | 2   | 5   | 4   | NG   | DRIP/모니터링 추상적, 측정 약 (2.5/4) |
| 18     | e5    | haiku  | 1   | 4   | 4   | NG   | priority 'high'인데 'monitor' category 부정합 (2.5/4) |
| 19     | e2    | sonnet | 2   | 5   | 4   | N/A  | 기술주 0%, 금융 0% 부재 섹터 식별 — 통찰 좋음 |
| 20     | e2    | sonnet | 1   | 4   | 4   | N/A  | '인컬' 오타 추정 1~2회 |
| 21     | e3    | sonnet | 1   | 5   | 4   | OK   | PEP 5% 축소 정량 + 음료/스낵 중복 (3/4) |
| 22     | e1    | haiku  | 1   | 4   | 4   | OK   | KO 20→15% 명시 + '유리이용률' 모호 표현 (3/4) |
| 23     | e4    | haiku  | 1   | 4   | 4   | N/A  | VZ 금리 민감도 + 5종목 집중도 통찰 |
| 24     | e3    | sonnet | 2   | 5   | 4   | OK   | 5~10% 비중 조정 + 음료/스낵 상관관계 (3/4) |

---

## §2. 분포 요약

### naturalness (24 cases)
- 5점: **10건** | 4점: **13건** | 3점: 1건 | 2~1: 0건
- 분포 폭: **3** (Slice 11 KPI ≥3 목표 충족)
- 평균: **4.375**

### insight (24 cases)
- 5점: **5건** | 4점: **17건** | 3점: 2건 | 2~1: 0건
- 분포 폭: **3**
- 평균: **4.125**

### actionability (12 EVAL cases)
- OK: **9건** (75%) | NG: **3건** (25%)
- N/A: 12건 (E2/E4/E6)

---

## §3. 모델별 분석 (Claude 평가 기준)

| 항목                  | haiku (n=12)              | sonnet (n=12)             | sonnet - haiku |
| --------------------- | ------------------------- | ------------------------- | -------------- |
| naturalness 평균      | 4.00                      | 4.75                      | **+0.75**      |
| insight 평균          | 4.17                      | 4.42                      | **+0.25**      |
| actionability OK rate | 5/6 (83%)                 | 5/6 (83%)                 | **±0**         |
| naturalness 5점 비중  | 1/12 (8.3%)               | 9/12 (75%)                | sonnet 압도   |
| 3점 출현              | 2건 (V2, V5·V11 insight=3) | 0건                      | haiku 약함     |

### Claude 예측 winner: **sonnet** (품질 우위)
- naturalness +0.75 격차 명확
- insight +0.25 미세 우위
- actionability 동률

### Efficiency 트레이드오프 (Part 4 측정)
- haiku: cost $0.00472 / latency 8.6s
- sonnet: cost $0.01510 / latency 15.9s
- sonnet은 **3.2× 비싸고 1.85× 느림**

### Part 5 결정 포인트
**품질 +0.75 점 (5점 만점 척도)가 cost 3.2× efficiency 절감을 정당화하는가?**
- 정당화: sonnet (품질 우선, 사용자 facing)
- 미정당화: haiku (efficiency 우선, 대량 배치)

---

## §4. 특이 케이스 메모

### schema FAIL (V16, e3 haiku #1)
- content는 5/5/OK로 매우 좋음 — HHI + ETF 간접 편중 통찰 우수
- 문제는 JSON 뒤 markdown 텍스트 ("## 📊 추가 코멘트") trailing
- **#41 keep_open 패턴**: prompt가 JSON-only 강제했음에도 haiku가 추가 분석 텍스트 첨부
- 개선 방향 (Phase B 부채): `parse_json_response` trailing tolerance (#58 후보 강화)

### NG 케이스 패턴 (3/12)
- V9 (e3 haiku #2): 수치 목표 명시 없음
- V17 (e5 sonnet #2): DRIP/모니터링 추상적
- V18 (e5 haiku #1): priority/category 부정합

→ **공통**: action_items의 measurability 부족. Slice 12+ rubric 강화 or prompt 보강 후보.

### 3점 출현 (insight 2건)
- V5 (e2 haiku #2): "데이터 나열" 위주
- V11 (e2 haiku #1): "데이터 나열" 위주
- **공통**: E2 haiku에서 insight 낮음. sonnet E2는 모두 4점.

---

## §5. Phase B에서 비교할 항목

1. **점수 일치율**: 병진 vs Claude 각 점수 동일/±1/±2 비율
2. **분포 폭**: 병진 ≥3 KPI 달성 여부
3. **winner 일치**: 병진의 모델별 평균과 Claude의 sonnet 예측 일치 여부
4. **NG 케이스 일치**: 병진 NG와 Claude NG 케이스 교집합
5. **schema FAIL 평가 분리**: V16 content는 좋지만 production 통합은 별개 문제 확인
