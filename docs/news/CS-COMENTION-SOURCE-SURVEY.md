# CS-COMENTION-SOURCE-SURVEY — 내러티브 그룹핑(R2) 연료 소스 실측 조사

> 2026-08-24, R1 지시서 Phase D. **read-only + 한정 probe(FMP 1콜·Marketaux 1콜[403]).** 통합·쓰기 0.
> **추천 미기재**(다음 결정 사이클 디렉터 스코어카드 몫). 실측 근거만 정리.

## 후보별 요약표

| 소스 | native multi-ticker | 근거(실측) | 예산/한도 | 통합 비용 | 태깅 정밀도 |
|---|---|---|---|---|---|
| **AV** NEWS_SENTIMENT(broad) | **YES** — broad 경로 avg **1.38 엔티티/기사·다중(2+) 9,523건** | 저장 데이터 실측(NewsEntity 68,255) | free **25 req/day**·1 req/s | **이미 통합·가동 중**. per-symbol은 04-25 의도 제거([[D-08]])·broad는 존치·복원코드 존재 | `ticker_sentiment.relevance_score`(0~1 정상, avg 0.818) |
| **Marketaux** /news/all | **YES(native)** BUT 현 통합이 단일심볼 질의로 **붕괴→다중 0** | 07-13 조사 + S2 라이브 2콜(entities=1 확증)·오늘 라이브 probe **403**(키 로테이션/제약 추정) | Basic **2,500/day**·30/min·20/req(헤더 실증) | broad/market 경로 신설 + **URL 정규화 통일**(AV raw↔MKX normalized 이중카운트) + **match_score 정규화**(비정규·avg 35.7) 선행 | `entities[].match_score`(비정규)·`highlights[]`(제목/본문 위치·AV보다 세밀)·per-entity sentiment |
| **FMP** /stable/news/stock | **NO** — 기사당 `symbol` **1개**·티커별 복제·entities 배열 없음 | D-3 라이브 1콜(symbols=AAPL,MSFT,NVDA→기사별 symbol 단일·NVDA12/MSFT3) | Starter 300/min·10k/day | URL 디둡+재그룹 필요(AV와 동일 약점)·다중 0(저장 36,295 전량 1.00) | 단일 symbol만·sentiment 없음 |
| **Polygon** v2/reference/news | **YES** — `tickers[]` 배열 + `insights[]`(per-ticker sentiment+reasoning) | 공식 docs(URL polygon→massive 이전·live fetch 404, knowledge 기준) | free **5/min**·2년 이력 | **shared 래퍼 신설**(계정 필요·현재 미보유)·URL dedup 정책 | `tickers[]` + **per-ticker sentiment**(후보 중 최고 정밀) |
| **Alpaca** v1beta1/news | **YES** — `symbols[]` 배열 | 공식 docs live fetch(symbols=array 확인) | free(계정)·분당 한도 doc 미명시(통상 ~200/min)·2015+ 이력 | shared 래퍼 신설(계정 필요) | `symbols[]`만·per-ticker sentiment 없음 |

## D-1 AV 상세 (probe 금지·코드/이력 기반)
- **per-symbol 뉴스 = 2026-04-25 의도적 제거**(멀티프로바이더 전환·DECISIONS 1206 "04-25 AV per-symbol 제거 ~ 07-08 broad 재개"). 우발 아님.
- **AV broad(NEWS_SENTIMENT)는 존치·가동**: `AlphaVantageNewsProvider.fetch_broad_news(time_from/time_to)`·beat `collect-av-broad-news`@01:00 UTC. co-mention 실질 견인(다중 9,523).
- 복원 재사용 코드: `fetch_broad_news`·`backfill_broad_news`(DECISIONS 5824~5827). 한도 free 25/day·서버측 쿼터([[D-AV-ACCOUNTING]]).

## D-2 Marketaux 상세 (기존 전수조사 `docs/news/marketaux_comention_survey_2026-07-13.md` + 오늘)
- `/news/all` 응답 = `entities[]{symbol,name,exchange,country,type,industry,match_score,sentiment_score,highlights[]}` — **native 다중티커**.
- 그러나 현 수집 `fetch_company_news(단일심볼+filter_entities)` → 엔티티 질의심볼로 축소 → **저장 marketaux 전량 1.00/기사·다중 0**. **갈림길=broad/market 경로(심볼 무필터·다중 보존) 신설 여부**.
- 플랜 Basic 2,500/day(X-Usagelimit-Limit 실증)·30/min. match_score 비정규(58.15·9.44)→정규화 계층 필요. dedup 비대칭(AV raw url vs MKX normalized)→이중카운트 위험(단 실측 AV 노출 ≈1행=경미).
- **오늘 라이브 probe(D-2 재확인 시도) = HTTP 403**: 키 존재하나 거부(로테이션/plan 제약/rate 추정). 재시도 안 함(상한·규칙 3). 기존 S2 라이브(07-13 200)로 스키마·붕괴 이미 확증됨.

## D-3 FMP 상세 (라이브 1콜)
- `/stable/news/stock?symbols=AAPL,MSFT,NVDA&limit=15` → 15기사·각 기사 `symbol` **단일**(entities 배열 없음)·분포 NVDA12/MSFT3 = **기사가 티커별로 복제**. 원본 `d3_fmp_multi.json`.
- 판정: **FMP는 native 다중티커 아님**. co-mention 쓰려면 URL 디둡 후 재그룹 필요(AV broad와 동일 후처리, 그러나 AV처럼 다중엔티티 원천이 없어 그룹 복원 근거 약함).

## D-4 신규 벤더 (probe 없음·docs)
- **Polygon**: `results[].tickers[]`(배열) + `results[].insights[]{ticker,sentiment,sentiment_reasoning}`. free 5 calls/min·2년 이력. 통합=shared 래퍼 신설·계정 발급 필요. **per-ticker sentiment까지 native = 태깅 정밀도 최상**.
- **Alpaca**: `news[].symbols[]`(배열)·headline/summary/content/source/url. 계정 free·이력 2015+. sentiment 없음. 통합=shared 래퍼 신설·계정 필요.

## 회계
- 외부 호출: FMP 1콜(D-3)·Marketaux 1콜(403·D-2)·AV 0(규칙 2)·Polygon/Alpaca probe 0(계정 없음·docs만). 전부 상한(각 3) 이내.
- 쓰기: 이 문서 생성만(D-5 산출물). 데이터/통합/스키마 쓰기 0.
