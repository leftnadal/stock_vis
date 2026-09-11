# SCB-CONTEXT-RECON — 맥락 층 재료 실측 보고 (읽기 전용)

> 세션: recon · 읽기 전용 · 코드/DB 쓰기 0 · 마이그 0 · **설계 금지(재료만)**. 발행 지시서 = SCB-CONTEXT-RECON(2026-09-10).
> 측정 DB = **개발 DB(stock_vis)** = 세션 구동 DB. ⚠ prod와 행 수가 다를 수 있음(어느 쪽이 운영인지 미확정 — 병진 확인 필요). 아래 수치는 전부 개발 DB 기준.

## §0 세션 헤더
- 구동 트리/브랜치: `~/worktrees/sv-scb-recon` · `monorepo/sess-scb-recon` · baseline origin/main `4ff6ef05`
- 외부 콜: **1/3** (`/stable/grades-historical?symbol=NVDA&limit=5` → 200 OK)
- health_check: ✅17 / ⚠1 / ❌0

**부수 ① health_check ⚠** (지시서 09-10 ⚠2 → 현재 **⚠1**):
- ⚠ = `런타임 감지 로그(runtime_check)` 최근 24h WARN(@2026-09-09 08:41 UTC·드리프트 24h+).
- **원인 판별**: runtime_check는 런타임 트리 드리프트 감지 로그 → **MGMT-BATCH-B(문서/git 전용·런타임 무접촉)가 아니라 09-04~10 다세션 런타임 활동** 유래(판별 가능). 09-10 시점의 2번째 ⚠는 이 스냅샷에 부재 → **정체 판별 불가**(추정 안 함).

**부수 ② deploy_history.log**: 존재·**15줄**(worker 2·web 7·api 6). **둘째 sync 이후 다회 기록 확인**(부트스트랩 공백 통과·D-DEPLOY-PATH-1 방어 라이브). 최근 3건 = 2026-09-07 16:01 (worker `01d39d86→5e4e70ea`·web `95c0583c→5e4e70ea`·api `01d39d86→5e4e70ea`).

---

## §A 현행 카드 baseline — "가격만 나온다"의 정확한 범위

성적판 = `GET /api/v1/coach/analyst-scorecard/?h=21`(compute-on-read·나안 TTL 캐시·전역·SCORING_VERSION=1). 산출 = `analyst_scoring.build_scorecard`(Tier1 3과목: direction_hit_rate·target_progress[63/126/252]·cross_sectional_ic).

**FE가 실제 렌더에 쓰는 필드(`frontend/types/scorecard.ts`)**:

| 레벨 | 필드 | 성격 |
|---|---|---|
| ScorecardSignal | direction·captured_at·spot_at_capture·target_price·maturity_date·status·**realized{close·return_pct·target_progress_pct·verdict}**·unscoreable_reason·pending_d_day·cohort | 전부 **가격/목표가/방향/판정** |
| ScorecardSymbol | symbol·counts{scored/pending/unscoreable}·hit{hits/total}·avg_target_progress·signals[] | 적중 집계 |
| ScorecardBoard | sample_n·significance_threshold·direction_hit·avg_target_progress·cross_sectional_ic | 보드 통계 |
| Reproduction | as_of·scoring_version·git_head·input_rows·splits_* | 재현 좌표 |

**현재 카드가 답하지 못하는 질문 (결핍 서술·설계 아님)**:
1. **"왜 그 등급이 나왔나"(논거)** — 등급 논거 텍스트 필드 자체가 응답에 없음.
2. **"그때 무슨 일이 있었나"(당시 맥락)** — 뉴스·이벤트 연결 없음.
3. **등급 분포·변화 추이** — 데이터(`grades_historical`)는 DB에 100% 존재하나 **카드에 미표시**(응답 스키마에 없음).

> `SCB-CARD-REUSE`가 언급한 `SignalCard`(증거 바 + 판정 문장) 컴포넌트 — FE 타입상 `verdict`/`realized`가 그 역할(증거 바=target_progress_pct, 판정 문장=verdict). 실 컴포넌트 파일 위치는 본 recon에서 미확인(설계 턴에서 확인).

---

## §B 애널리스트 논거·등급 이력 (1순위 재료)

```
[재료] AnalystSignalSnapshot.grades_historical
 원천   : packages/shared/stocks/models.py AnalystSignalSnapshot (JSONField)
 실재   : 있음 — 274행 전부 채움(100%)
 규모   : 274행 · 고유심볼 11 (GOOGL·TLN·AAPL 각 30 …)
 최신성 : captured_at 2026-08-03 ~ 2026-09-09 · writer beat ON(아래)
 좌표   : symbol+captured_at 둘 다 db_index — 조회 가능
 형태   : ★ 월별 **등급 카운트 추이**만 — 키 = date·symbol·analystRatingsStrongBuy/Buy/Hold/Sell/StrongSell.
          (AAPL 예: 04-01~09-01 월별 Buy/Hold/Sell 분포) **논거 텍스트 아님**
 비용   : 수집 완료(추가 비용 0)
 판정   : AMBER — 등급 *변화 추이·사건*은 카운트 델타로 유도 가능 / "왜(논거 텍스트)"는 담지 않음
```
```
[재료] 애널리스트 논거 텍스트 (newGrade·gradingCompany·action·newsTitle)
 원천   : FMP /stable/grades-historical (현 수집) · /stable/grades·grades-news (미구현)
 실재   : 없음 — 외부 콜 실측(NVDA limit5, 200 OK): 키 = analystRatingsBuy/Hold/Sell/StrongBuy/StrongSell·date·symbol.
          **논거/뉴스/개별 애널리스트 action 필드 전무**. FMPClient에 grades-news·개별 grades 메서드 부재.
 비용   : 신규 엔드포인트 + 신규 수집 파이프라인 필요(플랜 게이트 미확인 — 별 엔드포인트라 402 여부 별도)
 판정   : RED — 현 수집 경로로는 논거 텍스트 획득 불가
```
```
[재료] get_price_target_summary (publishers)
 원천   : packages/shared/api_request/providers/fmp/client.py:699
 실재   : 메서드 정의됨·writer 미사용(호출처 0) — 필드 = lastMonth/Quarter/Year/allTime AvgPriceTarget+Count+publishers
 판정   : AMBER — 발행처(publishers) 이름은 주나 논거 텍스트 아님 · 추가 콜 필요
```
- **writer 배선**: `apps.portfolio.tasks.ingest_analyst_signals` (beat `portfolio-analyst-signals-daily` **ON**·평일 19:30 ET·last_run **2026-09-09 23:30**). 4콜 = ratings_snapshot·price_target_consensus·grades_consensus·grades_historical (`analyst_signal_writer._fetch_signals`).
- 다른 필드 채움률: target_consensus/high/low/median·grade_strong_buy~·grade_consensus·rating·overall_score **전부 100%**. pinned(spot_at_capture 有) 234 / derived 40.
- 중복 수집 경계: `apps/chain_sight/services/estimate_service.py`가 `get_analyst_estimates` 사용(별 원천) + beat `chainsight-snapshot-analyst-estimates` ON — **컨센서스 재료를 다른 앱도 수집 중**(경계 판단은 설계 턴 몫).

---

## §C 당시 상황(news) 맥락 — #128 재발 검사 포함

```
[재료] NewsEntity (심볼+뉴스 연결)
 원천   : services/news/models.py NewsEntity (symbol db_index · news FK → published_at)
 실재   : 있음 — 614,279행 · 고유심볼 12,164
 최신성 : 최신 news 발행 2026-09-09 18:47 · 최근30d 77,167
 좌표   : symbol + news__published_at 범위 조회 실측 — NVDA 928건(460ms)·AAPL 372(198ms)·GOOGL 292(114ms) @ 30d전±3d → 실용적(sub-second)
 판정   : GREEN — 심볼+날짜로 당시 뉴스 복원 가능
```
```
[재료] NewsArticle / SentimentHistory / DailyNewsKeyword
 NewsArticle     : 484,305행 · 최신 2026-09-09 21:51 · 최근30d 63,901 → GREEN
 SentimentHistory: 48,641행 · 고유심볼 7,411 · 최신 2026-09-08 (symbol+date db_index) → GREEN
 DailyNewsKeyword: 193행 · 최신 2026-09-10 (date unique) → GREEN(저규모·일별)
```
```
[재료] StockNews — ★#128 반전
 원천   : packages/shared/stocks/models.py StockNews · 읽기 = services/.../news_source.py StockNewsSource
 실재   : 있음 — 98,583행 · 최신 2026-09-09 18:47  ← #128 "0행 죽은 테이블"에서 부활
 사유   : beat `newsfix-sync-stocknews`(services.news.tasks.sync_news_entities_to_stock_news) **ON** · last_run 2026-09-09 21:30
          (NEWSFIX-SYNC-BE b731d7b4, 09-02 착지분이 가동 중)
 판정   : GREEN — 단, TASKQUEUE·코드 주석("StockNews 0행·beat enabled=False·현 운영 상태 비어있음")이 전부 STALE → 갱신 필요
```

**#128 재발 검사표** (원천 생존 — 행수·최신·판정):

| 테이블 | 행 수 | 최신 | 판정 |
|---|---|---|---|
| NewsArticle | 484,305 | 2026-09-09 | 살아있음 |
| NewsEntity | 614,279 | 2026-09-09 | 살아있음 |
| SentimentHistory | 48,641 | 2026-09-08 | 살아있음 |
| DailyNewsKeyword | 193 | 2026-09-10 | 살아있음 |
| **StockNews** | **98,583** | **2026-09-09** | **부활(과거 0행)** |

---

## §D rag_analysis / Neo4j 층

```
[재료] rag_analysis 모델 (DataBasket·BasketItem·AnalysisSession·AnalysisMessage·UsageLog)
 실재/규모/최신 : DataBasket 593행(최신 2025-12-15) · BasketItem 0행 · AnalysisSession 34(2026-03-05) · AnalysisMessage 44(2025-12-16) · UsageLog 0행
 판정   : RED — 휴면(최근 활동 수개월 전·BasketItem/UsageLog 0행). 맥락 재료로 현행성 없음
```
```
[재료] Neo4j / RelationConfidence
 원천   : apps/chain_sight RelationConfidence(PG) + Neo4j sync
 실재   : RelationConfidence 14,072행 (serving_layer: context 9,365 · evidence 4,670 · pending 21 · excluded 16)
 생존   : NEO4J_URI=bolt://localhost:7687 · beat neo4j-health-check ON(last 2026-09-10 04:00) · sync-relations/news/profiles 전부 ON
          (Neo4j 노드/엣지 직접 카운트는 client import 경로 오류로 미수행 — beat 성공으로 생존 판정)
 판정   : AMBER — 살아있으나 '관계망' 재료(종목 간 관계)라 '애널리스트 논거·뉴스 맥락'과 직접 대응 아님. 재사용 형태 불명(설계 턴 몫)
```
- neo4j 큐 태스크 8종 중 health_check_neo4j·cleanup_expired_semantic_cache·warm_semantic_cache·get_semantic_cache_stats·sync_* 전부 beat 등록·ON(IMPLEMENTATION_SUMMARY 요약은 본 recon 미독·설계 턴 확인 권고).

---

## §E coach LLM 주입 지점 식별 (자리만 — 무엇을 넣을지는 설계라 제외)

| 진입점 | 프롬프트 경로 | 현재 입력 구성 | 토큰 예산 | 최근30d 실사용 |
|---|---|---|---|---|
| e1 | prompts/e1 | — | 5000 | **측정불가** |
| e2 | prompts/e2 | — | 1500 | 측정불가 |
| e3 | prompts/e3 | **AnalysisContext**(analysis_target_portfolio·wallet_background·watchlist_context) | **7000**(P90 4359) | 측정불가 |
| e3_portfolio | prompts/e3_portfolio | — | 7000 | 측정불가 |
| e4_tier1/2 | (advisory_engine) | portfolio context+question(+history) | 6000/8000 | 측정불가 |
| e5 | prompts/e5 | — | 2000 | 측정불가 |
| e6 | prompts/e6 | — | 1500 | 측정불가 |

- **`rationale/` 프롬프트 = 애널리스트 논거 아님**: `prompts/rationale/builder.py` = E4 답변 **품질 평가자**(Slice9 #44·4요소[현재상태/임계/액션/시점] 채점·호출 = `advisory_engine.py`). 이름이 '논거'라 오해 소지 — 맥락 주입용 아님.
- **맥락 주입 지점 1순위 = E3 `AnalysisContext`**(`apps/portfolio/schemas/analysis_context.py:134`·Pydantic·budget 7000). 현재 portfolio/wallet/watchlist 구성 → 맥락 필드 추가 여지 있음(방법은 설계 금지).
- **cost_ledger = DB 아닌 JSONL**(`docs/portfolio/coach/cost_ledger.jsonl`·append-only·31행·**최신 2026-05-26**). 4개월 stale → **진입점별 최근 사용량 측정 불가**(coach LLM 휴면이거나 로깅 경로 변경 — 미확정). 토큰 예산 초과 판단의 실사용 근거는 이 ledger로 불가.

---

## §4 최종 보고

```
[SCB-CONTEXT-RECON 착지 보고]
구동 트리/브랜치: ~/worktrees/sv-scb-recon · monorepo/sess-scb-recon · baseline 4ff6ef05
DB: 개발 DB(stock_vis) 기준 · prod와 상이 가능(운영 DB 미확정·병진 확인 필요)
외부 콜: 1/3 (/stable/grades-historical NVDA → 200·numeric-only 확증)

부수 ① health ⚠: runtime_check 24h WARN(09-09)=09-04~10 다세션 런타임 유래(판별 가능) · 09-10 2번째 ⚠는 스냅샷 부재로 판별 불가
부수 ② deploy_history: 15줄·둘째 sync 이후 다회 기록 有·최근 09-07 16:01

블록 A baseline: 응답 필드 = 가격/목표가/방향/판정 계열 전부 · 논거·맥락·등급분포 0 · 결핍 3줄
블록 B: grades_historical 100%채움이나 **등급 카운트 추이(논거 텍스트 아님)=AMBER** · 논거 텍스트=RED(FMP 미구현) · writer beat ON
블록 C: NewsEntity 614k·좌표쿼리 sub-second=GREEN · **StockNews 98k 부활(#128 반전·beat ON)=GREEN** · 코드/TASKQUEUE 주석 stale
블록 D: rag_analysis 휴면=RED · Neo4j/RC 14,072 생존=AMBER(관계망≠논거/뉴스)
블록 E: 주입지점 = E3 AnalysisContext(budget 7000) · rationale 프롬프트=품질평가자(논거 아님) · cost_ledger JSONL 4개월 stale=사용량 측정불가

종합 판정: GREEN 5 (NewsEntity·NewsArticle·SentimentHistory·StockNews·좌표쿼리) / AMBER 4 (grades_historical·price_target_summary·Neo4j-RC·E3주입지점) / RED 2 (논거 텍스트·rag_analysis)
가장 큰 미지수 1건: "왜 그 등급(논거 텍스트)"의 원천 — FMP 현 수집 경로엔 없음. 별 엔드포인트(grades/grades-news) 플랜 게이트(402) 미확인.
디렉터 결정 필요 사항(사실만):
  · 논거 축: 텍스트 원천 부재 → (a)등급 카운트 추이로 대체 표시 (b)신규 FMP 엔드포인트 수집 (c)news로 우회 — 택1은 설계 결정
  · 맥락 축: news 재료 GREEN(즉시 가용) · 주입 지점 E3 AnalysisContext 존재 · 어느 화면/경로에 붙일지는 설계 결정
  · 운영 DB 확정(개발 DB 실측이 prod와 같은지)
  · stale 문서 갱신(StockNews 0행·beat enabled=False 기록 · cost_ledger 로깅 경로)
HALT/예외: 없음 (완주·읽기 전용 준수·설계 미작성)
```
