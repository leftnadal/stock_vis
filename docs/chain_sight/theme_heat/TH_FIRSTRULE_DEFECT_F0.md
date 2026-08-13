# TH-FIRSTRULE-DEFECT — F0 진단 (읽기전용, 수정 0)

> 작성: 2026-07-13 검증 세션. 베이스라인 `aaaf495` (worktree `~/worktrees/sv-theme-heat`).
> 성격: **읽기전용 진단** — 코드·원장 무변경. 산출물 = 215건 사유 클래스 계량표 + "ai" 세부 + 비준 대상 전략 권고.
> 원천 데이터: `docs/chain_sight/theme_heat/h2_firstrule_recheck.json` (TH-14 작업2, "무적용" 동결본, LLM 재검).

---

## 0. 결론 요약 (먼저 읽기)

1. **지시서 전제 정정 — 부분문자열 과매칭은 실재하지 않는다.**
   매처는 이미 **토큰-정확(exact-token) 방식**이다. `apps/chain_sight/services/c3_narrative_service.py:71-90` `match_term_to_sectors`:
   단일어 시드 → `kw in tokens`(공백 split 후 집합 멤버십, 88行), 다중어 시드 → 구절 포함(`kw in norm`, 85행), 주석 명시 **"부분 문자열·유사도 금지"**.
   → 지시서가 가정한 `"ai"가 maintain/chair/campaign에 걸림`은 **코드상 불가능**. 실측으로도 "ai" 매칭 85건 **전부 온전한 단어 "AI"**(부분문자열 0건).
   → **후속 세션은 부분문자열 버그를 찾지 말 것. 없다.**

2. **215건의 지배 원인은 "온전한 단어 토큰의 의미상 오배정"** — 절반 이상이 **애초에 어느 섹터 테마에도 속하면 안 되는 매크로/잡음 term**(should_be=`none` **101건 = 47%**).

3. **원장 영향 정정.** 이 215건은 **뉴스 term → 섹터 배정**(C3 파이프라인, `ThemeNewsVolume` mention 집계)이다.
   ETF/주식 → 테마 배정(`ThemeMatch`, `serverless_theme_match`)과 **별개 저장소**다.
   → F3 영향 지표는 "테마별 **구성종목 수**"가 아니라 "테마별 **뉴스 term/mention 수**"이며, 재배정은 **테마 온도의 C3 성분 z**에 영향을 준다(구성종목 아님). 지시서 F3 문구를 이 축으로 교체 권고.

4. **지시서 4개 수정 전략의 실제 커버리지가 F0로 계량됨(§3).** ⑴(단어경계)은 **커버 0건**(이미 exact). 지배 지렛대는 **⑷ 사전 정정 + ⑶ 모호·매크로 토큰 스톱리스트**.

---

## 1. 4-클래스 계량표 (합 215)

| # | 클래스 | 건수 | 정의(운영) | 대응 전략 |
|---|--------|-----:|-----------|-----------|
| C1 | 부분문자열 과매칭 | **3** | 매칭 토큰이 온전한 단어가 아님 | 실질 0 — 3건은 **복수/굴절 경계**("data center"∈"data centers", "nonfarm payroll"∈"nonfarm payrolls")인 다중어 구절 포함 케이스. 지시서가 말한 부분문자열(maintain/chair)류 **0건** |
| C2 | 부수 언급(단일토큰 오배정) | **50** | 온전한 단일 토큰이 매칭됐으나 term의 실제 주제가 타 섹터(기업 GICS 우선) | ⑶ 스톱리스트 + 개별 예외 |
| C3 | 우선순위 오류(복수토큰) | **48** | 복수 섹터 토큰 매칭, 더 구체적 규칙 대신 덜 구체적/유니온이 선점 | ⑵ 특이성 우선순위 |
| C4 | 사전/유니버스 오류(pseudo-theme·drop) | **114** | 매크로 pseudo-테마 버킷 배정 OR should_be=`none` | ⑷ 사전 정정 + ⑶ 스톱리스트 |

- 재검 원본 축(참고): `rule_defect` 197 / `individual_exception` 18. `individual_exception` 18건은 규칙 수정이 아닌 **term별 개별 예외 오버라이드** 대상(예: "JPMorgan AI agents"→FinSvc, "EV bus adoption India"→Industrials).
- C4 세부: 오배정 버킷 = Macro 37 · Crypto 29 · Geopolitical 21 · Technology 20 · Regulation 3 · ESG 1 ···. should_be = **none 100** · Technology 6 · Financial Services 5 ···.
  → **핵심**: 사전에 **투자 섹터가 아닌 pseudo-테마 버킷(Macro/Crypto/Geopolitical/Regulation/ESG)** 이 존재하고, 매크로 토픽 term이 그리로 흘러들어간다. 이 버킷들은 재검 판정상 대부분 `none`(테마 부적격)으로 강등돼야 한다.

## 2. "ai" 토큰 세부 (지시서 기지 75건)

- `defect_token_freq`상 "ai" = **75**(rule_defect 최다). match_tokens에 "ai" 포함 레코드는 **85건**(rule_defect 75 + individual_exception 10).
- **85건 전부 온전한 단어 "AI"** — 부분문자열 과매칭 **0**. 예: `JPMorgan AI agents`, `Meta AI engagement`, `industrial AI adoption`, `Trump AI council`.
- 실제 사유 분포(85건):
  - should_be=`none` **22건** — "AI" 토픽 자체가 섹터 테마 아님(예: `AI copyright law`, `AI disruption fears`, `Trump AI council`).
  - 기업 GICS 우선(K2 위반) — `JPMorgan AI *`(→Financial Services), 등. Technology로 오배정되나 term 주제는 특정 기업/타 섹터.
  - 우선순위(복수토큰) — `industrial AI adoption`(ai+industrial→should Industrials), `Keel Infrastructure AI`(ai+infrastructure→should Industrials).
- 시사: "ai"는 **단독 토큰으로는 섹터 신호가 아니다**. → 스톱리스트(⑶) 또는 사전에서 제거/맥락화(⑷) 대상. 단어경계(⑴)는 무의미.

## 3. 비준 대상 — 전략별 실측 커버리지

| 전략 | 커버 | F0 실측 근거 |
|------|------|-------------|
| ⑴ 단어경계/전체토큰 매칭 | **0건** | 매처가 이미 exact-token. 부분문자열 실재 0. **채택 불필요(NO-OP)** |
| ⑵ 특이성 우선순위 | ~**48건**(C3) | 복수 섹터 토큰 매칭 시 "가장 구체적/기업 GICS" 우선 규칙 도입 필요(현재 유니온/선점) |
| ⑶ 모호·매크로 토큰 스톱리스트 | ~**83건** | `should_be=none` 101건 중 **83건**이 매크로/모호 토큰(ai·fed·inflation·crypto·geopolitical·regulation·china·bitcoin·stablecoin·rate hike·tech·bond·ipo·tariff···)만으로 매칭 → 스톱리스트로 완전 해소. 훅 이미 존재: `c3_narrative_service.py:50` `MATCH_EXCLUDE_TOKENS = frozenset()`(빈 집합) |
| ⑷ 사전 정정 | ~**114건**(C4) | `KEYWORD_SECTOR_MAP`(`services/news/services/keyword_sector_map.py`)에서 pseudo-테마 버킷 토큰 제거/재라벨 + `"ai":"Technology"`(15行) 등 다의 토큰 정리 |

**권고 채택안 = ⑷ + ⑶ 우선, ⑵ 보조, ⑴ 폐기.**
- 1차: ⑷ 사전에서 매크로 pseudo-테마 토큰 정리 + ⑶ `MATCH_EXCLUDE_TOKENS` 확장 → C4·C2 대부분(~130건) 해소.
- 2차: ⑵ 복수토큰 시 특이성 우선 → C3 48건.
- 잔여: `individual_exception` 18건은 H2 사전(`ThemeKeywordH2`)의 term별 오버라이드로 흡수(규칙 아님).

## 4. 코드·데이터 좌표 (F1 착수용)

- 1차 규칙 매처: `apps/chain_sight/services/c3_narrative_service.py:71-90` (`match_term_to_sectors`).
- 스톱리스트 훅(빈 집합): 같은 파일 **50행** `MATCH_EXCLUDE_TOKENS`.
- 집계·영속화: 같은 파일 `aggregate_theme_news_volume` 93-140行 → `ThemeNewsVolume`(`apps/chain_sight/models/heat.py:381-402`).
- 토큰 사전: `services/news/services/keyword_sector_map.py` `KEYWORD_SECTOR_MAP`(10行~), 문제 항목 `"ai":"Technology"` 15行.
- H2 2차 사전(DB): `ThemeKeywordH2`(`apps/chain_sight/models/heat.py:405-444`), 시드 `seed_theme_keyword_h2.py`.
- 215건 원장(matched-token + 정정 섹터): `docs/chain_sight/theme_heat/h2_firstrule_recheck.json` `misassigned_list`.
- 선행 결정: DECISIONS 결정17(스테이지 매처), TH-14 작업2(215 등재), TASKQUEUE `TH-FIRSTRULE-DEFECT`(등재만, 미집행).

## 5. 안전 원칙 재확인 (F1~F3 비준 조건)

- 원장 변경(재배정)은 **되돌림 경로 필수** — 기존 배정 이력 보존.
- 재배정 = 방법론 변경 → **개정일 마커** 등재 → 해당일 delta/driver 자동 보류(결정29/31 재사용). `affected_themes`(결정30)에 재배정 영향 테마 집합 기록.
- 프론트 노출은 재배정 검증 완료 전까지 **게이트 차단**(TH-15 선례 = 편향 온도 선노출 금지).

## 6. 비준 요청 (F1~F3 착수 전 결정 필요)

1. **채택 전략**: ⑷+⑶ 우선 / ⑵ 보조 / ⑴ 폐기 — 승인?
2. **pseudo-테마 버킷(Macro/Crypto/Geopolitical/Regulation/ESG) 처리**: 전량 `none` 강등(재검 판정 따름) vs 일부 보존?
3. **원장 축 확정**: 재배정 영향 = `ThemeNewsVolume`/C3 성분(구성종목 아님). F3 지표를 이 축으로 재정의 승인?
4. **H2 사전 적용과의 관계**: TH-FIRSTRULE-DEFECT(1차 규칙)와 TH-C3-LLM-DICT(H2 사전 박제, `h2_recheck_v1.json` keep635/reassign32/demote4)를 **묶어서 한 번의 재집계**로 vs 분리?
