# CS-S3 8번 후속 — co-mention 쌍 출처 계측 (T-1~T-5)

- **세션**: CS-RESUME-DEPLOY, 2026-09-15
- **성격**: 읽기 전용 계측. **판정·코드 수정 없음.** 다음 결정 사이클(S3-2)의 재료.
- **DB**: prod (dev=prod 공유), 쓰기 0건

---

## 요약 — 디렉터 근인③은 반증, 근인②는 구조적으로 큼

| | 가설 | 계측 결과 |
|---|---|---|
| 근인③ | "대량 종목 기사가 쌍을 폭증시킨다" | ❌ **반증**. 10종목 이상 기사 = 전체 460,384건 중 **5건**, 그로부터만 유래한 쌍 304개 중 CoMentionEdge에 실재하는 것 **0건(0.00%)** |
| 근인② | "ChainNewsEvent.symbol 이 제목의 주어가 아니다" | ⚠️ **확인**. 표본 50건 중 주어 적중 **18건(36%)** |

---

## T-1 · 기사당 종목 수 분포

**최근 90일** (엔티티 보유 기사 200,200건, 최대 5종목)

| 구간 | 기사 수 | 쌍 수 ΣC(N,2) |
|---|---:|---:|
| 1 | 172,454 | 0 |
| 2 | 13,064 | 13,064 |
| 3 | 7,055 | 21,165 |
| 4 | 3,845 | 23,070 |
| 5–9 | 3,782 | 37,820 |
| 10+ | **0** | **0** |
| 합계 | 200,200 | 95,119 |

**전체 기간** (460,384건, 최대 **15**종목, 평균 1.36)

| 구간 | 기사 수 | 쌍 수 |
|---|---:|---:|
| 1 | 375,030 | 0 |
| 2 | 40,683 | 40,683 |
| 3 | 20,873 | 62,619 |
| 4 | 11,978 | 71,868 |
| 5–9 | 11,815 | 118,225 |
| **10–19** | **5** | **347** |
| 20+ | 0 | 0 |
| 합계 | 460,384 | 293,742 |

> 최근 90일 최대가 5인 것은 기간 아티팩트다. 전체 기간 최대는 15이며 해당 기사는 **5건**뿐.

## T-2 · 구간별 쌍 비중 (최근 90일)

2종목 13.7% · 3종목 22.3% · 4종목 24.3% · 5–9종목 39.8% · **10+ 0.00%**

전체 기간 기준 10+ 구간 기여 = 347쌍 = **0.12%**.

## T-3 · CoMentionEdge 중 "10+ 기사에서만" 유래한 쌍

| | 값 |
|---|---:|
| 10+ 기사에서 나온 쌍 | 347 |
| 10미만 기사에서 나온 쌍 | 87,326 |
| **10+ 기사에서만** 나온 쌍 | 304 |
| CoMentionEdge 실제 쌍 | **38,116** |
| **교집합** | **0 (0.00%)** |

> ⚠️ 축 주의: 디렉터 지시서의 "CoMentionEdge 4,251건"과 실측 **38,116**은 다른 축이다(필터·창 미상). 위 비율은 전체 38,116 기준.

## T-4 · daily_spike 후보 중 위 집합 비율

단일일·`co_mention_count>=5`·최근 14일 후보 쌍 = **10건**.
그중 "10+ 기사에서만" 유래 = **0 (0.0%)**. 10+ 기사에 등장하기라도 하는 쌍 = **0 (0.0%)**.

## T-5 · ChainNewsEvent.symbol 이 제목의 주어인가 (표본 50, seed 20260915)

**주어 적중 18/50 = 36%**

판정 규칙: 제목 문자열에 ⑴ 티커가 단어 경계로 등장 **또는** ⑵ 회사명 첫 유의어(법인격어 제외)가 등장.

불일치 예시:

| symbol | 회사명 | 제목(앞부분) |
|---|---|---|
| INTC | Intel Corporation | Advanced Micro Devices, Inc. stock: Is AI dominance now t… |
| NVDA | NVIDIA Corporation | Babcock & Wilcox (BW) AI Ride Propels 191% Jump This Year |
| YUM | Yum! Brands, Inc. | 3 Reasons ALNT is Risky and 1 Stock to Buy Instead |
| MSFT | Microsoft Corporation | Tech-Fueled Rally Meets a Dividend Squeeze at the iShares MSCI World ETF |
| AMZN | Amazon.com Inc. | Is Netflix Better Off Without Roku or Warner Bros.… |
| STX | Seagate Technology Holdings | Western Digital Stock Rockets 52% With 6-Day Winning Streak |
| DLTR | Dollar Tree, Inc. | 11 Best New Cracker Barrel Kitchen Finds Shoppers Love This Week |
| AAPL | Apple Inc. | The S&P 500 Is Nearing Record Highs, but This 1 Unstoppable ETF… |
| RTX | RTX Corporation | Burney Co. Decreases Position in Lockheed Martin Corporation $LMT |
| SO | The Southern Company | Georgia Power offers ways to save on rising summer energy bills |

**측정 한계(하한값이라는 뜻)**: 규칙이 자회사·브랜드명을 놓친다(예: `SO`↔"Georgia Power"는 실제로는 올바른 귀속일 수 있음). 따라서 36%는 **주어 적중률의 하한**이다. 다만 INTC↔AMD 제목, NVDA↔Babcock & Wilcox 제목, DLTR↔Cracker Barrel 제목처럼 **명백한 오귀속**이 표본에 다수 존재한다.

---

## 계측이 말하는 것 (해석 아님, 수치의 직접 함의만)

1. 묶음이 이상해지는 원인은 **기사가 종목을 많이 달아서가 아니다** — 그런 기사는 사실상 없다(5건·기여 0.12%·CoMentionEdge 기여 0건).
2. 남는 후보는 **⑴ 제목/근거 선택의 대표성**(T-5: `symbol`이 제목 주어가 아닌 비율이 최소 64%)과 **⑵ `_enrich_titles`가 group 카드인데 seed 쌍 1개로만 조회**하는 구조다. 둘 다 S3-1 스모크 8번에서 관측된 현상(GOOG·QCOM 카드에 AMZN 제목)과 직접 부합한다.
3. daily_spike 후보 쌍은 최근 14일 기준 **10건**뿐이다 — 묶음 품질 문제는 **소량 표본에서 발생**하며, 대량 노이즈 제거가 아니라 **선택 규칙 교정**의 문제로 보인다.
