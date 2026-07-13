# Marketaux 보조 co-mention 소스 — 전수 조사 (STEP 0 세션, 2026-07-13)

> 지시서 ⑥. **조사 전용** — 구현·수정 없음. read-only. 목적: 설계 결정 입력 확보.
> 브랜치 `monorepo/sess-mkx-survey`, base origin/main `0d981de`.
> **Marketaux 실호출 0건** (스키마·밀도 모두 저장 데이터로 충족 — AV rolling 함정 교훈, 외부 가정 최소화).

---

## 요약 (한 줄)

Marketaux → `services.news` NewsEntity → co-mention 경로는 **구조적으로 이미 연결**돼 있고 7,148개 NewsEntity가 존재하지만, **현재 저장된 marketaux 엔티티는 기사당 정확히 1.00개(다중엔티티 0건)** 라서 **co-mention 기여가 실질적으로 0**이다. 원인은 수집이 `fetch_company_news(symbol=단일, filter_entities=true)` 경로로만 들어와 기사당 심볼이 1개로 붕괴하기 때문. **설계의 갈림길은 "단일심볼 company 경로"가 아니라 "다중엔티티를 보존하는 broad/market 경로"를 여느냐에 있다.**

---

## 항목 1 — 통합 현황 (실측)

### 1-a. 클라이언트/래퍼 위치 — **packages/shared 경유 아님**
- Provider: `services/news/providers/marketaux.py` → `class MarketauxNewsProvider(BaseNewsProvider)`.
- **`packages/shared`에 없음.** (외부 API 규약상 shared 경유가 기대되나 현재는 `services/news` 내부 직속.) → 경계 관점 기록(수정 안 함).
- `BASE_URL = https://api.marketaux.com/v1`, endpoint `/news/all`.

### 1-b. 소비 주체 — **두 경로, 저장 대상이 다름**
| 소비자 | 파일 | 저장 모델 | co-mention 기여 |
|--------|------|-----------|------------------|
| `NewsAggregatorService` | `services/news/services/aggregator.py:34` (`self.marketaux`) | `services.news` **NewsArticle + NewsEntity** | ✅ 가능 (extract_co_mentions가 NewsEntity 읽음) |
| market_pulse `news_aggregator` | `apps/market_pulse/services/news_aggregator.py:74` (`_build_marketaux_provider`, delay=0) | **MarketPulseNews** (`mp_news` 테이블, 별도) | ❌ NewsEntity 미생성 → co-mention 무관 |

- 즉 **co-mention에 유효한 marketaux는 `services.news` 경로뿐**. market_pulse의 시간당 `mp_fetch_news_hourly`(활발히 가동 중, 최근 07-13 00:05 UTC)는 별도 모델로 흘러 co-mention과 무관.

### 1-c. 실제 수집 가동 여부 (beat/TaskResult 실측, 조사시각 2026-07-13 01:04 UTC)
- `services.news` marketaux 수집 beat = **enabled·평일(dow=1-5) 스케줄**, 정상 등록:
  - `collect-market-news-{morning h8/evening h18}` (id=56/23), `collect-daily-news-{morning h6/afternoon h14}` (id=54/55), `collect-category-news-*` (id=26/27/58) — 전부 tz=America/New_York, **last_run=2026-07-10(금)**.
  - 07-11(토)·07-12(일) 미발화 = **평일 스케줄의 정상 주말 공백**(장애 아님). 07-13(월)부터 재개 예정.
- ⚠️ **STALE 중복 beat 발견 (Bug #28 패턴 — 기록만, 수정 안 함)**: 동일 작업이 두 task 경로로 이중 등록.
  - `news.tasks.collect_daily_news` (id=21), `news.tasks.collect_category_news` (id=28) = **구 경로**(`services.` 접두 없음) — 워커에 미등록 경로일 가능성(unregistered task 위험).
  - `services.news.tasks.collect_daily_news` (id=54), `services.news.tasks.collect_category_news` (id=26 등) = 정상 경로.
  - → 경계/위생 이슈. co-mention 설계와 별개로 정리 대상.
- 데이터 신선도: marketaux_uuid 기사 최신 published_at **2026-07-10 21:46 UTC**, 일별 생성 06-29~07-11 구간 **~150~200/일** 유지(주말 감소).

---

## 항목 2 — entities[] 스키마 (저장 데이터 + provider 파싱 실측)

Marketaux `/news/all` 응답 아이템 (provider 주석 + `_parse_article` `marketaux.py:191-299` 기준):
```
{ uuid, title, description, url, image_url, published_at, source,
  entities: [ { symbol, name, exchange, country, type, industry,
                match_score,          # 심볼-기사 매칭 신뢰도
                sentiment_score,      # 엔티티별 감성
                highlights: [ { highlight, sentiment, highlighted_in: title|main_text } ] } ] }
```
- **본문 매칭 방식**: `filter_entities=true` 파라미터 + `symbols=` 필터. `highlights[]`가 본문/제목 어디서 매칭됐는지(`highlighted_in`)까지 제공 — AV보다 세밀.
- provider → `NewsEntity` 매핑: `symbol / entity_name / entity_type / exchange / country / industry / match_score(Decimal) / sentiment_score / source="marketaux"`, `highlights[]` → `EntityHighlight`(Marketaux 전용 모델, `models.py:231`).
- **신뢰도(match_score) 데이터 품질 주의**: 저장된 marketaux match_score **avg ≈ 35.7**, 전량 0.9 초과 버킷 = **0~1 정규화 안 됨**(모델 validator 0~1이나 update_or_create가 full_clean 미수행). 원시 스케일 그대로 저장된 듯. 설계 시 정규화 필요. (AV match_score avg 0.818 = 0~1 정상.)

---

## 항목 3 — 파이프라인 접점

- **저장 지점**: `services/news/services/aggregator.py::_save_articles`(172) → `_save_article`(URL upsert) → created 시 `_save_entities`로 `NewsEntity` + `EntityHighlight` 생성. **AV·FMP·Marketaux 공통 경로**(provider 무관 통일).
  - 단, updated(기존 URL) 기사엔 `if not article.entities.exists()` 일 때만 엔티티 추가(202) → 이미 엔티티 있으면 2차 provider 엔티티 **미병합**(밀도 손실 지점).
- **co-mention 합류**: `apps/chain_sight/tasks/relation_tasks.py::extract_co_mentions`(19)는
  `NewsEntity.objects.filter(news__published_at__gte=cutoff)` → 기사별 그룹 → `.filter(cnt__gte=2)`.
  **provider 무필터 확인** — source 상관없이 NewsEntity면 자연 합류. **변환 계층 불필요.**
- **∴ 구조적으로는 이미 합류 가능.** 병목은 구조가 아니라 **데이터 형상**(아래 밀도).

---

## 항목 4 — 중복 전략 재료 (이중 카운트 위험)

- **dedup 키 = URL exact** (`_save_article`: `NewsArticle.objects.get(url=...)`), `url_hash`=URL SHA256.
- **정규화 비대칭 (위험 핵심)**:
  - Marketaux: `url=self.normalize_url(...)` **호출** (`marketaux.py:285`) — 소문자화 + 쿼리스트링 전체 제거 + 트레일링 슬래시 제거.
  - AV: `url=item.get("url")` **정규화 미호출** (`alphavantage.py:183,242`) — 원시 URL.
  - → **같은 기사라도 AV(raw)와 Marketaux(normalized)의 저장 URL이 달라 exact match 실패 → NewsArticle 이중 생성 → NewsEntity 이중 → co-mention 가중치 왜곡** 위험.
- **deduplicator는 배치 내부 전용** (`deduplicator.py`): url_hash set + 제목유사도 0.85(`SequenceMatcher`). **DB/cross-provider 비교 없음** → 서로 다른 시각에 도는 AV·Marketaux 배치 간 중복은 못 잡음.
- 재료 결론: Marketaux를 co-mention 소스로 합류시키려면 **AV↔Marketaux URL 정규화 통일** 또는 **DB단 cross-provider dedup(정규화 URL 기준)** 선행 검토 필요.

---

## 항목 5 — 예산·플랜 (문서/설정/코드 기준, 실증 항목 표시)

- 코드/설정 **가정**: `config/settings.py:99` `marketaux.per_day=2500`, provider 주석 "Basic Plan 2,500 calls/day, 20 articles/request", `get_rate_limit()`={2500/86400s}.
- **기사당 entities 상한**: request당 `limit=20`(Basic), `filter_entities=true` 시 필터 심볼만 반환.

### ★ 실증 추기 (지시서 ⑦ S2, 2026-07-13, 실호출 2건)

응답 **헤더에 쿼터가 노출**됨 — 대시보드 없이 실증 가능:

| 항목 | 실증값 (헤더) | 판정 |
|------|--------------|------|
| 일 한도 | `X-Usagelimit-Limit: 2500` | **Basic 플랜 확정** (코드 가정 정확 — free 100 아님) |
| 일 잔여 | `X-Usagelimit-Remaining: 2496` (2호출 후) | 금일 사용 소량 → 확장 여유 큼 |
| 분당 버스트 | `X-Ratelimit-Limit: 30`, `Remaining: 29` | 분당 30 (provider `request_delay=10s` = 안전 여유) |
| 리셋 방식 | 일일(daily) usage 카운터. **정확한 리셋 시각(UTC 자정?)은 헤더 미노출 = 미실증** | 웹 문서도 리셋 시각 명시 없음 |
| match_score 스케일 | 라이브 58.15·9.44 (unbounded relevance) | 0-1도 0-100도 아님 → **S4 정규화 근거** |

- 웹 확인(marketaux.com 문서는 403이나 검색 결과): **free 플랜 ≈ 100 req/day** — 하지만 이 계정 키는 **Basic 2500**(헤더 실증)이므로 free 제약 무관.
- **결정적 재확증**: `symbols=AAPL,MSFT`+`filter_entities=true` 실호출인데도 기사당 `entities=1`(AAPL만) 반환 → survey의 "단일심볼 붕괴로 co-mention 무익" **라이브 확증**.
- **A 재결정 입력**: 일 2500 여유(현 사용 ~수십/일) → broad/market 경로(심볼 무필터, 다중엔티티 보존) 신설이 한도상 충분히 가능. 리셋 시각만 확장 전 실증 권장(잔여=0 도달 시점 관찰).

---

## 항목 6 — 테스트 현황 (하위 Explore 에이전트 조사)

- **안전(mock/monkeypatch)**: `test_providers.py`(requests.get 패치, `TestMarketauxNewsProvider`), `test_services.py`(`mock_settings` fixture로 `settings.MARKETAUX_API_KEY`/`FINNHUB_API_KEY` monkeypatch), `test_fmp_provider.py`(Mock client).
- 🔴 **NEWS-AGG-TEST-ENV 재발 지점 확인**: `tests/unit/news/test_aggregator_savepoint.py:34` `NewsAggregatorService()` **직접 인스턴스화**, fixture/mock 없음.
  - `aggregator.py:25-37`가 `FinnhubNewsProvider(api_key=settings.FINNHUB_API_KEY)` / `MarketauxNewsProvider(api_key=settings.MARKETAUX_API_KEY)`를 **무조건** 생성 → env 부재 시 기본값 `''` → provider `__init__`의 `if not api_key: raise ValueError(...)` → **테스트 실패**.
  - 대조: `apps/market_pulse` 경로는 `_build_marketaux_provider`가 키 없으면 `None` 반환(안전). **`services/news` 경로만 강제 의존.**
- 설계 시 marketaux 수집 확장하면 이 강제-키 생성자 패턴이 격리환경 테스트를 계속 깨뜨릴 소지.

---

## AV 대비 커버리지 소견 (저장 데이터 실측)

| source | NewsEntity | 기사수 | avg 엔티티/기사 | **다중(2+) 기사** = co-mention 후보 |
|--------|-----------:|-------:|----------------:|------------------------------------:|
| alpha_vantage | 68,255 | 49,565 | **1.38** | **9,523** |
| fmp | 36,295 | 36,295 | 1.00 | 0 |
| **marketaux** | **7,148** | 7,148 | **1.00** | **0** |
| finnhub | 11 | 6 | 1.83 | 5 |

- **핵심**: marketaux는 전량 **기사당 1심볼** → **co-mention 직접 기여 현재 0**. 원인 = `fetch_and_save_company_news`가 `self.marketaux.fetch_company_news(symbol, filter_entities=true)`(aggregator.py:91)로 **단일 심볼 질의** → `filter_entities`가 엔티티를 질의 심볼로 축소.
- AV broad(다중엔티티 9,523)가 co-mention을 실질 견인 중. Marketaux가 같은 역할을 하려면 **심볼 필터 없는 broad/market 경로에서 다중 엔티티를 보존**해야 함.
- 기사량 체감: marketaux ~150~200/일(services.news 경로) vs AV broad 전일 2창 ~1,800/일 → **볼륨도 AV가 ~10배**.

---

## 설계 결정 갈림길 후보 (판단 보류 — 재료만)

1. **수집 경로**: (A) 기존 `NewsAggregatorService` 합류 — 단, 단일심볼 company 경로는 co-mention 무익 → **broad/market 경로(다중엔티티 보존) 신설/전환**이 전제. vs (B) AV broad처럼 **별도 marketaux broad 수집 트랙** 신설.
2. **dedup 선행 여부**: AV↔Marketaux **URL 정규화 통일**(AV에 normalize_url 적용) 또는 **cross-provider DB dedup** 선행 없이는 이중 카운트로 co-mention 가중치 왜곡. → dedup 선행 **필요**로 기운다(재료상).
3. **match_score 정규화**: 저장 marketaux match_score 0~1 밖(avg 35.7) → co-mention 가중치에 쓰려면 정규화 계층 필요.
4. **엔티티 병합 정책**: 기존 URL 기사에 2차 provider 엔티티 미병합(`_save_articles:202`) → 병합 허용 시 밀도↑지만 dedup·중복과 상호작용.
5. **플랜 한도 실증**: 확장 전 무료/Basic 플랜 실한도·리셋 방식 **실호출 1건으로 실증** 필요(이번 세션은 의도적 0건).
6. **테스트 위생**: 확장 시 `NewsAggregatorService` 강제-키 생성자 → 격리 fixture(키 monkeypatch 또는 조건부 provider) 선행.
7. **경계**: provider가 `packages/shared` 아닌 `services/news` 직속 + STALE 중복 beat(#28) — 확장과 별개 정리 후보.

---

## Marketaux 실호출 회계

- **조사 세션(지시서 ⑥): 총 0건.**
- **위생 세션(지시서 ⑦ S2): 총 2건** (상한 ≤2 준수, 문서 확인 선행):
  - #1 `2026-07-13T01:30:31Z` `GET /v1/news/all?limit=3&filter_entities=true` → HTTP 200, 헤더로 쿼터 실증.
  - #2 `2026-07-13T01:31:12Z` `GET /v1/news/all?symbols=AAPL,MSFT&limit=2&filter_entities=true` → HTTP 200, match_score 라이브(58.15·9.44) + 단일심볼 붕괴 확증.
  - Usage-Remaining 2497→2496. AV 호출 0·프로브 0 유지.

## 조사 방법 회계

- 전부 read-only: 코드/설정 정적 분석 + `services.news`/`django_celery_beat`/`django_celery_results` DB **SELECT**(운영 DB, 무변경). AV 호출 0·프로브 0. 코드·설정·모델·beat 무변경.
