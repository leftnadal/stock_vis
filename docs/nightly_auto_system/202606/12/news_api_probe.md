# 뉴스 API 호출 실패 핀포인트 진단 (news_forensic 후속)

- **일시**: 2026-06-14 진단 (증상 관찰 06-12)
- **증상**: 뉴스 페이지 전 섹션(키워드·언급종목·카테고리) 빈 상태. 콘솔 `Failed to fetch all news — newsService.ts:181`.
- **성격**: read-only 핀포인트. 수정 0, 프로세스 0, DB write 0. curl/grep/로그만.
- **저장**: `monorepo/sess-mgmt`. 조사 코드 기준 = 라이브 dir `stock_vis`(`sess-mp-kl-f1f3`).

> 어제 news_forensic의 "API ✅"는 shell queryset 재현(HTTP 미검증) 기반 — 본 진단이 그 갭을 메워 **결론을 정정**한다. 어제 주원인 H4(카테고리 계약)는 **2차 요인**이고, 실제 차단은 **HTTP 401**이다.

---

## 1. 호출 URL 복원 + 실측 상태 코드

- **base**: `API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'`
- **env 실측**: `frontend/.env.local` → `NEXT_PUBLIC_API_URL=http://localhost:18765/api/v1` (daphne 포트, LISTEN 확인). **mtime May 26 — 키 회전과 무관.**
- **공통 prefix**: `services/newsService.ts`의 **모든** 함수가 `${API_URL}/news/...` 공유. 헤더는 `Content-Type`만 — **Authorization 토큰 미전송**(raw `fetch`, authAxios 미사용).

| 엔드포인트 | 실측 HTTP | permission |
|-----------|:---------:|-----------|
| `/news/all/?source=all&category=all&days=7&limit=100` | **401** | (미지정 → 기본 IsAuthenticated) |
| `/news/daily-keywords/` | **401** | 미지정 |
| `/news/insights/` | **401** | 미지정 |
| `/news/trending/` | **401** | 미지정 |
| `/news/sources/` | **401** | 미지정 |
| `/news/market-feed/` | 200 | `[AllowAny]` (콜드스타트) |
| `/news/interest-options/` | 200 | `[AllowAny]` (온보딩) |

401 바디: `{"status_code":401,"detail":"자격 인증 데이터가 제공되지 않았습니다.","code":"not_authenticated"}` (Content-Type application/json, 0.004s).

---

## 2. 원인 확정문

> **DRF `DEFAULT_PERMISSION_CLASSES`가 2026-04-29 `IsAuthenticatedOrReadOnly → IsAuthenticated`로 강화(commit `3a0b76f`, audit P0 "GET 무차별 노출 차단")됐는데, 공개 의도의 뉴스 read 엔드포인트(all/daily-keywords/insights/trending/sources 등)에 `[AllowAny]` 면제를 주지 않아 전부 401. 프론트 `newsService`는 토큰 없는 raw fetch라 401 → 뉴스 페이지 전 섹션 공백.**

- 라우트는 정상 응답(401 = 인증 필요, 404 아님) → 서버·라우팅 정상.
- market-feed/interest-options만 명시적 `[AllowAny]`라 200 → AI 브리핑 카드만 동작, 나머지 공백.
- **6주간 잠복**: 4/29 변경 이후 줄곧 401 상태였을 것(newsService가 토큰을 보낸 적 없고, 프론트 3000↔API 18765 cross-origin이라 세션쿠키도 미전송). 사용자가 6/12 페이지 진입 시 비로소 관찰. 어제 forensic은 HTTP 미검증이라 놓침.

---

## 3. 가설 판정

| 가설 | 판정 | 근거 |
|------|------|------|
| **H5** 라우팅 잔여물(구 경로 404) | **기각** | `config/urls.py:38` = `include("services.news.api.urls")`(신), `settings.py:196` INSTALLED_APPS=`services.news`(신). 상태코드 401(≠404). 라우팅 정상. |
| **H6** 키 회전 env 부작용 | **기각** | `frontend/.env.local` mtime **May 26**(회전 6/10~ 무관), 값 정상(18765). 401은 JWT 권한이지 회전된 외부 API 키와 무관. |
| **H7**(신규) 권한 정책 강화 미면제 | **지지(주원인)** | DEFAULT IsAuthenticated(4/29) + 뉴스 read 엔드포인트 AllowAny 누락 + newsService 무토큰 fetch. |
| H4(어제) 카테고리 계약 불일치 | **유효하나 2차** | crypto/forex/merger 빈 탭은 별개 결함. 단 현재는 401로 general 탭조차 못 받으므로 H7이 선결. |

---

## 4. 잔여물 전수 (수정 지시서 재료 — 실해/무관 표기)

### 4-A. 주원인 수정 대상 — AllowAny 미지정 뉴스 read 엔드포인트 (services/news/api/views.py)
> 401 반환 중. 공개 의도면 `[AllowAny]` 부여, 인증 필요면 프론트 authAxios 전환 — **정책 결정 선결**.

| 액션 | 행 | 현 상태 |
|------|---:|--------|
| `all_news` (`/all`) | 398 | 미지정 → 401 (뉴스 카테고리 섹션) |
| `daily_keywords` | 539 | 미지정 → 401 (오늘의 키워드) |
| `keyword_detail` | 676 | 미지정 → 401 |
| `insights` | 856 | 미지정 → 401 (언급 종목) |
| `market` | 255 | 미지정 → 401 |
| `trending` | 325 | 미지정 → 401 |
| `sources` | 488 | 미지정 → 401 |
| `stock_news`/`stock_sentiment` | 82/137 | 미지정 → 401 |
| `recommendations` | 1337 | 미지정 → 401 |
| `news_events`/`impact-map` | 1067/1130 | 미지정 → 401 |
| (참고) `market_feed`/`interest_options` | 957/1001 | **[AllowAny] → 200** (모범) |
| (참고) admin류 ml-*/collection-logs/pipeline-health | — | `[IsAdminUser]` (의도된 보호) |

### 4-B. 프론트 (services/newsService.ts)
- 전 함수 raw `fetch` + `Content-Type`만 (무토큰). 401 시 `throw` → 빈 상태. **빈/에러 분기 없음**(silent fail로 섹션 공백). 실해(현 증상 직접).

### 4-C. 구 경로 잔여물 (H5 무관·별개 거버넌스, 어제 발견 재확인)
| 위치 | 내용 | 판정 |
|------|------|------|
| `services/serverless/views_admin.py:114/122/130` | task 문자열 `news.tasks.collect_daily_news` 등 (구 경로) | **실해·무관** — admin 트리거 시 미등록 task명(`services.news.tasks.*`가 정답) → NT-7 패턴. 현 401과 무관. |
| PeriodicTask `collect-daily-news`, `collect-category-news-medium` | `task=news.tasks.*` (구 경로), enabled, last_run 6/12 | **실해·무관** — beat 발사되나 worker에서 미등록 task일 가능성(KeyError). NT-11 계열. 현 401과 무관. |
| `config/management/commands/celery_errors.py:99` | 주석 예시 `news.tasks...` | **무해** — 문자열 예시. |

---

## 5. 라우팅 분류 의견

- **app(news/@backend) — 주 트랙**: 4-A AllowAny 정책 결정 + 부여. 뉴스 페이지는 콜드스타트 공개 의도(market-feed가 이미 AllowAny)이므로 **공개 read 엔드포인트에 `[AllowAny]` 부여가 설계 정합**. 보안 강화(4/29)가 공개 뷰 면제를 누락한 것을 메우는 작업.
- **app(frontend) — 보완**: 만약 "뉴스는 로그인 필수" 정책이면 newsService를 authAxios로 전환(Bug #26 클래스) + 빈/에러 상태 UI. 정책에 따라 A 또는 B 택1.
- **ops — 별개**: 4-C 구 경로 잔여물 정리(serverless admin dict + PeriodicTask 2건)는 재배치 후속 = ops/@backend 영역. **현 증상과 무관하나 NT-7/NT-11 미해결 부채로 잔존.**
- **H5/H6 모두 기각** → 라우팅 잔여물·env 트랙 아님. 핵심은 **권한 정책(app/@backend) 단일 결정**.

---

## 부록 — 실측치
- 변경 커밋: `3a0b76f` (2026-04-29) "audit P0 후속" — settings.py L360-362 DEFAULT_PERMISSION_CLASSES=IsAuthenticated.
- 서버: daphne(Python PID 30787) 127.0.0.1:18765 LISTEN, Next.js(node) :3000.
- 401 엔드포인트 5/5 동일 코드·바디 = 단일 원인(권한). 200 = AllowAny 2종.
