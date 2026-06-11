# 뉴스 카테고리 미작동 전수조사 (read-only forensic)

- **일시**: 2026-06-11 (조사 시점 03:12 EST / 16:12 KST)
- **증상**: UI 뉴스 카테고리 진입 시 뉴스가 거의/전혀 안 보임 (사용자 관찰)
- **성격**: ops 트리아지 — 측정·판정만. 수정 0, 프로세스 조치 0.
- **조사 코드 기준**: 라이브 dir `/Users/byeongjinjeong/Desktop/stock_vis` (`monorepo/sess-mp-kl-f1f3`, worker/beat 구동 dir). 보고서 저장 = `monorepo/sess-mgmt`.

> ⚠️ **방법론 경고 (재발 방지)**: 본 조사 중 "파이프라인 8h 정지"로 오판할 뻔했으나, `CELERY_TIMEZONE=America/New_York`를 확인하여 **정상 EST 야간 공백**으로 정정함. DB/로그 타임스탬프 KST 표시 ↔ 스케줄 EST 해석 불일치가 함정. (DECISIONS "STEP 0 측정에 git fetch 선행 의무화"와 동일 계열 — 기준선 확정 전 판정 금지.)

---

## 1. 뉴스 도메인 지도

| 층 | 파일 경로 | 소유자 (카드 기준) |
|----|----------|-------------------|
| **모델** | `services/news/models.py` (NewsArticle, NewsEntity, NewsCollectionCategory, NewsCollectionLog, DailyNewsKeyword 등) — `db_table=news_articles`, `app_label=news` | @backend 앱 (`services.news`) |
| **수집 태스크** | `services/news/tasks.py` (collect_daily_news, collect_market_news, **collect_category_news**, collect_sp500_news_fmp_*, classify_news_batch, analyze_news_deep) | @backend / @infra(beat) |
| **provider** | `services/news/providers/{finnhub,marketaux,fmp}.py` | @backend |
| **점수화** | `services/news/services/news_classifier.py` + `ml_*` (importance_score = Engine C 규칙) | @backend (NT-2b) |
| **API view** | `services/news/api/views.py` → `NewsViewSet` (`/api/v1/news/`) | @backend |
| **프론트** | `frontend/app/news/page.tsx` + `frontend/components/news/NewsCategorySection.tsx` (+27 컴포넌트) | @frontend |

**⚠️ 소유 불일치 발견**:
- **경로 불일치**: 코드는 `services/news`에 거주(`app_label=news`)인데, TASKQUEUE **NT-2b/NT-6 목적지 라벨이 "apps/news"**. 실제 `apps/news` 디렉토리는 **부재**. → 라우팅 라벨이 물리 경로와 불일치 (거버넌스 항목).
- 루트 `CLAUDE.md`는 `news | /api/v1/news/*` + `@backend`가 `news/` 소유로 명시 → app_label 기준으로는 정합. 단 "news/" 표기가 실제 `services/news/`를 가리킴은 카드에 미명시.

---

## 2. 퍼널 판정표

| 단계 | 판정 | 근거 |
|------|------|------|
| **수집** (provider→DB) | ✅ (정상) | collect-* crontab은 **EST 영업시간(06–18 EST) 스케줄**. 조사 시점 03:12 EST = 야간 → 미발사가 정상. `is_due=False, next=+8.8h`(collect-market-news-noon). Finnhub 키 200·수집 지속, `mp_fetch_news_hourly` 매시 수집. **B-1: created 14일 매일 162–947건, 6/11도 485건.** |
| **저장** (row 존재) | ✅ | NewsArticle **46,540행** / 최근7일 published **3,852건**. 데이터 충분. |
| **점수** (importance_score null) | ⚠️ | null **전체 81.3%(37839/46540) / 24h 88.4%(739/836) / 48h 85.8%**. classify는 EST 영업시간 스케줄이라 야간 누적분은 미점수 — 일부는 타이밍, 그러나 절대 수준은 NT-2b(임계/ML 채움) 지속 이슈. |
| **API** (서버가 내줌) | ✅ | 프론트는 `/api/v1/news/all/?source=all&category=all&days=7&limit=100` 호출. queryset = `published_at__gte(7일)` + category/source 필터만. **importance_score 필터·exclude 없음** → null이어도 반환. 7일 3,852건 반환 가능. |
| **렌더** (화면 표시) | ❌ **(단절 지점)** | 프론트 4탭 `[general, crypto, forex, merger]` 중 **crypto/forex/merger는 DB에 0건** → 영구 빈 탭. general 탭만 데이터. |

### 가설 판정

| 가설 | 판정 | 근거 |
|------|------|------|
| **H1** stale 프로세스가 구 키 보유 | **기각** | 현 worker(PID 30767, **6/11 11:12 KST 기동**) + worker-neo4j(30780) 모두 신규 키 보유(TR-6 검증). beat(61077, 6/10 23:07)·daphne(신규)도 회전 후. 구 키 프로세스 잔존 0. |
| **H2** 401 구간 수집 공백 → 최근 뉴스 부재 | **부분 지지(경미)** | Marketaux 401 **6/11 06:05–11:05 KST(14건)** 구간 Marketaux 수집 실패(키 회전 11:12로 복구, 현재 200). 그러나 Finnhub·FMP·mp_fetch는 지속 → DB에 최근 뉴스 충분. "안 보임"의 주원인 아님. |
| **H3** null 필터로 표시 누락 | **기각** | `/news/all`·`market`·`stock` 엔드포인트 어디에도 `importance_score` filter/exclude/정렬 없음. null 무관하게 반환. |
| **H4** API·프론트 자체 결함 | **지지 (주원인)** | 프론트 `DISPLAY_CATEGORIES=[general,crypto,forex,merger]`가 **DB에 존재하지 않는 category값**. 수집은 모든 기사를 `company(25753)/general(16498)/business(3130)/top news(1159)`로만 저장 → crypto/forex/merger **영구 0건**. `CATEGORY_MAP`은 company→general 매핑이라 general 탭만 채워짐. |

**근본 원인 결론**: **H4** — 프론트 카테고리 탭(crypto/forex/merger)과 실제 수집 데이터(category=company/general/business/top news)의 **계약 불일치**. 4탭 중 3탭이 구조적으로 항상 빈 상태. 사용자가 그 탭 진입 시 "전혀 안 보임". general 탭은 정상(전 카테고리가 general로 매핑되어 ~100건 표시).

---

## 3. 단절 지점별 다음 액션 후보 (⚠️ 실행하지 않음 — 후보만)

### app 소유 (@backend / @frontend — 주 트랙)
1. **카테고리 계약 정합** (주원인 H4) — 택1:
   - (a) 프론트 `DISPLAY_CATEGORIES`에서 빈 탭(crypto/forex/merger) 제거 또는 "데이터 없음" 빈 상태 UI 명시,
   - (b) 수집 단계에서 NewsArticle.category를 crypto/forex/merger로 분류하는 로직 추가(현재 provider가 company/general만 부여),
   - (c) 프론트 탭을 실제 존재 category(company/general/business)로 재정의.
2. **importance_score 채움률** — NT-2b 영역(임계 0.7 + ML 채움). 점수 엔진 트랙.
3. **PeriodicTask task 경로 정합** — `collect-category-news-medium`/`collect-daily-news` 등 일부 항목 `task=news.tasks.X`(구 경로), `-morning/-afternoon`은 `services.news.tasks.X`. 구 경로는 미등록 태스크명 위험(NT-7 패턴) — 실발사 여부 점검 후보.

### ops 소유 (프로세스·스케줄 위생)
4. **수집 재개 확인** — 6/11 06:00 EST(19:00 KST) collect-* 정상 발사 + Marketaux 신규 키로 200 수집되는지 **다음 EST 영업시간에 관찰**(현재는 정상 야간 공백이라 조치 불요).
5. **타임존 표기 가드** — 운영 보고서/로그에 EST(스케줄) ↔ KST(표시) 병기. 본 조사의 오판 유발 요인.

### 사용자 수동
- **없음.** 프로세스 재기동 불요(H1 기각·수집 정상). 키 회전은 이미 완료(TR-3~6).

---

## 4. 기존 NT 트랙 델타 (신규 번호 부여 안 함)

| 트랙 | 기존 | 본 조사 실측(2026-06-11) |
|------|------|------------------------|
| **NT-2b** (importance_score null) | 6/6 80.1% | **24h 88.4% / 48h 85.8% / 전체 81.3%** — 정체 지속. 절대 채움량 미증가. |
| **NT-6** (뉴스 커버) | 9.5%(5/x) | 종목연결률 최근7일 **71.3%**(2748/3852), 전체 67.7%. 보고서 "종목커버 44.7%"는 distinct 종목 기준(다른 지표). |

**신규 발견(NT 미귀속, app 소유)**:
- **NEWS-CAT-CONTRACT** (가칭): 프론트 카테고리 탭 ↔ DB category 계약 불일치 (H4 주원인). 기존 NT와 겹치지 않는 신규 app(news/frontend) 발견 → 라우팅 스텁 후보.

---

## 부록 — 핵심 수치 (read-only 실측)

- TZ: `CELERY_TIMEZONE=America/New_York`, `Django TIME_ZONE=Asia/Seoul`. 조사 NOW = 2026-06-11 07:12 UTC = 16:12 KST = **03:12 EST**.
- 키(마스킹): FINNHUB `(len=40, head=d8kl***)` ping **200**, MARKETAUX 신규 `(len=40, head=y1rt***)` ping **200**.
- 프로세스(KST 기동): worker 30767 11:12 / worker-neo4j 30780 11:12 / beat 61077 (6/10)23:07 / daphne 신규. 전부 회전 후.
- category 분포(전체): company 25753 / general 16498 / business 3130 / top news 1159. **crypto·forex·merger = 0**.
- DailyNewsKeyword: 6/11 completed(n=54), **6/7~6/10 전부 failed** — AI 브리핑/키워드 카드는 6/11 회복.
- Marketaux 401: 6/11 06:05–11:05 KST(14건), 11:12 키 회전 후 복구.
