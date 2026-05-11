# Slice 4 Part 2 완료 보고 (Slice 4 종결)

## §A. 환경 정합성

- git branch: `portfolio` (origin/portfolio rebase 완료)
- 회귀: portfolio 단독 baseline 160 → **173 passed (+13)**, 목표 +8~13 충족
  - 합산 표시 296 passed는 origin rebase로 머지된 marketpulse v2 +123 포함분 (Slice 4 작업과 무관)
- CostGuard 종결 상태: `slice_id="slice4"`, `call_count=15`, `total_cost_usd=$0.1576`

## §B. Step별 진척

| Step             | 산출물                             | LLM 호출      | 회귀 변화 | 시간                           |
| ---------------- | ---------------------------------- | ------------- | --------- | ------------------------------ |
| 6                | smoke + #9 latency 임계 적용       | 1             | 0         | (보고 수치 미수신, 추정 ~10분) |
| 7                | token 측정 + budget 등록 + 단위 +3 | 0             | +3        | (추정 ~15분)                   |
| 8                | 회고 + 그룹 + e6 entry 임시        | 14 + 재시도 0 | 0         | (추정 ~30분)                   |
| 9                | #2 통합 + 단위 +10                 | 0             | +10       | ~25분                          |
| report + backlog | 산출물                             | 0             | 0         | (추정 ~15분)                   |
| **합계**         | —                                  | **15**        | **+13**   | (단독 측정 미수신)             |

## §C. 신규 / 수정 파일

지시서 §C 명세 그대로 반영 가정 (14 신규 + 3 수정). 실제 commit 6건 — Part 1 종결 후 Part 2 신규 commit 분량 별도 보고 미수신.

## §D. Step별 핵심 결과

### Step 6

- LLM: latency=**9,180ms** (16,000ms 임계 57.4%), cost=**$0.00437** ($0.020 임계 21.8%)
- 4 판정: schema/completeness/cost/latency **모두 PASS**
- fallback_from: 보고 미수신 (정상 가정 — fallback 발생 시 명시되었을 것)
- fixture: e5_baseline_decrease (1차 smoke, 333 tokens)

### Step 7

- 7 fixture 실측: **P90=845**, mean=768, range 725~845
- budget 결정: **e6=1500 tokens** (P90 × 1.5 = 1,267.5 → round-up 500 단위)
- 사전 추정 1,000 정확도: **+50% 편차** ❌ (목표 ±20% 미충족)
- **이슈 β**: 한국어 토큰화 비율 ~1.3 char/token이 사전 추정 chars/3 휴리스틱보다 무거움. Slice 5 Step 0 부채 #β1로 등록

### Step 8

- 14 calls 비용: 보고 미수신 (Slice 4 단독 $0.1576에서 Step 6 $0.00437 차감 → Step 8 ≈ $0.153)
- lex_pass_rate: **haiku 7/7 (100%)**, **sonnet 7/7 (100%)** — 둘 다 ≥50% 충족
- label_means efficiency: **haiku 21.7590**, sonnet 7.7294 → **차이 14.0296 (haiku 2.815×, 64.5% 우세)**
- **Winner: haiku** (5% 임계 12.9× 초과 — 동률 위험 0)
- 그룹 분석 4매트릭스: 보고 상세 수치 미수신 — validation_report §3에 인용 필요
- **글쓰기 가설 외삽 검증: 4/4 정착** ✓

### Step 9

- 통합 함수: `_main_unified` (e1/e2/e6) + e5 delegation 유지
- Slice 1 IDENTICAL: **True** ✓ (`917fa3ef…0f7b9` 동일)
- Slice 3 IDENTICAL: **True** ✓ (`5594c6ab…f3ba` 동일)
- 시간: **~25분 / 30분 한도** (안전 마진 5분)
- **이슈 δ**: e5 delegation 자체는 정상이나 score_step8_e5 argparse exit 2. Step 9 도입 전부터 동일, 회귀 영향 0. 신규 백로그 #18로 등록

## §E. 케이스 A~F 발생 여부

| 케이스                         | 결과         | 미발동 근거              |
| ------------------------------ | ------------ | ------------------------ |
| A (Step 6 schema 실패)         | **미발생**   | schema_pass=True         |
| B (Step 6 latency > 16,000ms)  | **미발생**   | 9,180ms (57.4%)          |
| C (Step 8 호출 마진 < 5)       | **미발생**   | 15/50 종결, 마진 35      |
| D (Step 9 IDENTICAL 깨짐)      | **미발생** ✓ | Slice 1·3 모두 hash 일치 |
| E (Step 9 30분 한도 초과)      | **미발생**   | ~25분 종결               |
| F (winner sonnet, 가설 재평가) | **미발생**   | winner=haiku, 4/4 정착   |

## §F. 누적 비용

| 슬라이스                  | 협의 (메인 4스텝)               | 광의 (전체 호출 합)                           |
| ------------------------- | ------------------------------- | --------------------------------------------- |
| Slice 1                   | $0.122 (메모리) / $0.137 (보고) | $0.137 (재실행 1 + 진단 5 포함 추정)          |
| Slice 2                   | (보고서 본문 추적 필요)         | $0.19 (1차 손실 14건 포함)                    |
| Slice 3                   | $0.10                           | $0.10                                         |
| **Slice 4**               | **$0.1576**                     | **$0.1576**                                   |
| 누계 (방식1: 헤더 추적)   | $0.41 + $0.1576 = **$0.568**    | $0.49 + $0.1576 = **$0.648**                  |
| 누계 (방식2: 본문 재집계) | (방식1과 동일 가정)             | $0.137 + $0.19 + $0.10 + $0.1576 = **$0.585** |

⚠️ **이슈 γ**: 광의 누계가 방식1·방식2에서 어긋남 ($0.648 vs $0.585, 차이 $0.063). Slice 1 헤더 vs 본문 ($0.137 vs $0.122) 차이 + Slice 2 헤더 정의 모호성이 누적된 결과. **Slice 5 Step 0 부채 #γ1로 등록**.

## §G. Slice 4 KPI 체크리스트

- [x] 회귀: 단독 +13 (목표 +8~13)
- [x] LLM 호출 마진: 15/50 (마진 35, 안전 ≥ 5)
- [x] Step 9 IDENTICAL: Slice 1 + Slice 3 모두 통과
- [x] D4 round-trip 위반: 0건 (보고에 명시되지 않았으나 케이스 A~F 미발동으로 간접 확인)
- [x] 글쓰기 가설 외삽 검증: **4/4 정착**
- [ ] validation_report 6 섹션 작성: 보고 미수신 (작성 가정)
- [ ] refactor_backlog Slice 3 9건 처리 결과: **Slice 4 처리 2건 + Slice 5 이연 6건 + 신규 6건** (Slice 3 9건 중 #10 처리 미명시 — 검증 필요)
- [x] CostGuard 누적: `slice4` 등록, `call_count=15` 정상

## §H. Slice 5 진입 결정 자료

부록 F.1 비교표(이번 응답 산출물 2)로 위임. 권장: **E3 (preset 외삽 검증)** — 가중합 4.70/5.00.

## §I. Slice 5 사전 결정 보존 권장

부록 F.4 템플릿(slice5_decisions.md)에 사용자 결정 시 다음 항목 기재 — Slice 5 Part 1 작성 직전 시점에 작성.

---

## 종결 발견 요약 (5개)

1. **글쓰기 가설 4/4 정착** — Slice 5 외삽 위험 해소. preset 매트릭스 진입 안전
2. **haiku 우세 격차 확대** — Slice 1 142% → Slice 4 181%, 추세 일관
3. **token budget 한국어 휴리스틱 결함** — 1차 추정 +50% 편차, Slice 5 Step 0 보정
4. **누적 비용 헤더/본문 정합 누적 부채** — $0.063 차이, Slice 5 Step 0 재집계
5. **e5 argparse exit 2** — 잠재 부채, 신규 백로그 #18 등록 (PS 1.0)
