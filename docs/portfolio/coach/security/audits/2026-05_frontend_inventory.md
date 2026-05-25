═══════════════════════════════════════════════════════════════
[audits/2026-05_frontend_inventory.md] 프론트엔드 현황 조사 (read-only)
═══════════════════════════════════════════════════════════════

## 메타

| 항목 | 값 |
|------|----|
| 일자 | 2026-05-22 |
| 입력원 | `ls`, `find`, `package.json`, `package-lock.json`, `npm ls`, `grep` (코드 변경 0) |
| 비용 | $0 |
| 목적 | Slice 15(프론트 코치 화면) 진입 결정 + C-1 분기 base 사전 파악 |

---

## A. 존재·위치

- 프론트엔드 디렉터리: **`frontend/`** (저장소 루트, monorepo)
- 후보 검사:
  - EXISTS: `frontend/` (Next.js)
  - ABSENT: `client/`, `web/`, `src/`, `app/`, `static/`
  - EXISTS: `templates/` — Django 템플릿 (`admin/sec_pipeline`만, React 빌드 아님)
- `frontend/` 2단계 디렉터리:
  ```
  frontend/__tests__/{chainsight, thesis, validation}
  frontend/app/{admin, ai-analysis, chainsight, dashboard, login,
                market-pulse, market-pulse-v2, mypage, news, portfolio,
                screener, signup, stocks, thesis, watchlist}
  frontend/components/{admin, auth, chainsight, charts, common, eod,
                       financial, keywords, layout, macro, market,
                       market-pulse, news, portfolio, rag, screener,
                       stock, stocks, strategy, thesis, validation,
                       watchlist}
  frontend/{constants, contexts, hooks, lib, providers, services, types, utils}
  frontend/lib/{api, i18n, stores, thesis, utils}
  frontend/public/{icons, static}
  ```

---

## B. 프레임워크·툴링

### B-1. `frontend/package.json` 표기 (조사 시점)

**dependencies**:
- `@microsoft/fetch-event-source: ^2.0.1`
- `@tanstack/react-query: ^5.90.5`
- `axios: ^1.13.1`
- `clsx: ^2.1.1`
- `date-fns: ^4.1.0`
- `js-cookie: ^3.0.5`
- `lucide-react: ^0.546.0`
- `next: 16.0.0` (exact)
- `react: 19.2.0` (exact)
- `react-dom: 19.2.0` (exact)
- `react-force-graph-2d: ^1.29.1`
- `react-markdown: ^10.1.0`
- `recharts: ^3.3.0`
- `sonner: ^2.0.7`
- `tailwind-merge: ^3.3.1`
- `zustand: ^5.0.8`

**devDependencies**:
- `@tailwindcss/postcss: ^4`
- `@testing-library/{jest-dom, react, user-event}: ^6.9.1 / ^16.3.2 / ^14.6.1`
- `@types/{node, react, react-dom}: ^20 / ^19 / ^19`
- `@vitejs/plugin-react: ^6.0.1`
- `eslint: ^9`
- `eslint-config-next: 16.0.0`
- `jsdom: ^29.0.2`
- `tailwindcss: ^4`
- `typescript: ^5`
- `vitest: ^4.1.4`

### B-2. 핵심 스택 (`npm ls --depth=0` resolved)

| 도구 | 버전 | 비고 |
|------|------|------|
| Next.js | **16.0.0** | App Router (`frontend/app/`) |
| React | **19.2.0** | |
| react-dom | **19.2.0** | |
| TypeScript | 5.9.3 | `tsconfig.json` `strict: true`, paths `@/*` + `@contracts/*` |
| Tailwind CSS | 4.1.15 (+ `@tailwindcss/postcss 4.1.15`) | |
| TanStack Query | 5.90.5 | 서버 상태 |
| zustand | 5.0.8 | 클라이언트 상태 |
| axios | 1.13.1 | HTTP 클라이언트 (`lib/api/client.ts`, `lib/api/authAxios.ts`) |
| js-cookie | 3.0.5 | (실사용: localStorage 단일 소스 — B-3 참조) |
| eslint | 9.38.0 | `eslint-config-next 16.0.0` |
| vitest | 4.1.4 | |
| jsdom | 29.0.2 | |

- Lock 파일: **`package-lock.json`** (yarn.lock / pnpm-lock.yaml 부재)
- 전이 의존성 포함 트리 줄 수: **1443** (`npm ls --all | wc -l`)
- `extraneous` 표시 5건: `@emnapi/core@1.9.2`, `@emnapi/runtime@1.9.2`, `@emnapi/wasi-threads@1.2.1`, `@napi-rs/wasm-runtime@0.2.12`, `@tybys/wasm-util@0.10.1`

---

## C. 저장소 구조

- **monorepo** (Django 백엔드 + Next.js 프론트엔드 동일 저장소, `frontend/`가 하위 디렉터리)
- 현재 git 브랜치 (조사 시점): `slice14`
- `frontend/` 최근 커밋 3건:
  - `3159edb` (2026-05-13) — `test(frontend): validation+chainsight 컴포넌트 테스트 18개`
  - `444c6c1` (2026-05-12) — `fix(api): audit P0 #14 envelope 단일화 — thesis/etf/theme (PR-D) (#19)`
  - `3fafb68` (2026-05-12) — `fix(api): audit P0 #14 envelope 단일화 — serverless screener (PR-C) (#18)`

---

## D. 현재 완성도

- 코드 규모(`node_modules`/`.next` 제외):
  - 전체 `.ts`/`.tsx`: **360 파일**
  - `app/` 라우트 파일(`page.tsx` + `layout.tsx`): **27 파일**
  - `components/`: **202 파일**
  - `services/`: 18 파일
  - `hooks/`: 32 파일
  - `lib/` `.ts`/`.tsx`: 18 파일
- 스캐폴드 아님 — 다수 실제 화면 구현됨.

### D-1. `app/page.tsx` 라우트 전수
- `/`, `/admin`, `/ai-analysis`
- `/chainsight`, `/chainsight/[symbol]`, `/chainsight/watchlist`
- `/dashboard`, `/login`
- `/market-pulse`, `/market-pulse-v2`
- `/mypage`, `/news`, `/portfolio`, `/screener`, `/signup`
- `/stocks/[symbol]`
- `/thesis/(list)`, `/thesis/[thesisId]`, `/thesis/new`
- `/watchlist`

### D-2. `/portfolio` 페이지 (대표 예)
- `frontend/app/portfolio/page.tsx`: `portfolioService.getPortfolios()` + `getPortfolioSummary()` 호출, grid/table·pie/bar 토글 UI 구현.
- `frontend/components/portfolio/`: `PortfolioStockCard.tsx`, `PortfolioSummary.tsx`, `PortfolioChart.tsx`, `PortfolioModal.tsx`, `RealtimePortfolio.tsx`, `PortfolioTable.tsx`.

---

## E. 백엔드 연동 현황

### E-1. API 클라이언트 파일
- `frontend/lib/api/config.ts` — `API_BASE_URL` 정의
- `frontend/lib/api/client.ts` — axios 인스턴스 (`baseURL = API_BASE_URL`)
- `frontend/lib/api/authAxios.ts` — **JWT 인터셉터 단일 소스** (401 시 `/users/jwt/refresh/` 자동 호출)
- `frontend/lib/api/marketPulseV2.ts` — market-pulse v2 전용

### E-2. 호출 엔드포인트 (`api.*`/`authAxios.*` sort -u)

| 도메인 | 엔드포인트 |
|--------|----------|
| users | `/users/portfolio/`, `/users/portfolio/summary/`, `/users/portfolio/<id>/`, `/users/portfolio/symbol/<symbol>/[status/]`, `/users/watchlist/[<id>/[stocks/[<symbol>/[remove/]]]/[add-stock/]]`, `/users/jwt/refresh/` |
| serverless | `/serverless/{movers, movers/<symbol>, breadth, heatmap/sectors, health, screener, screener/chain-sight, presets, presets/<id>[/share], presets/shared/<code>, presets/import/<code>, alerts, alerts/<id>[/toggle], alerts/history[/<id>/{read,dismiss}], keywords/<symbol>, keywords/batch, keywords/generate-all, keywords/generate-screener, keywords/<symbol>/regenerate, thesis/my-theses, thesis/<id>, thesis/generate, sync, sync-now, admin/dashboard/{actions[/status/<task>], market-pulse, news[/categories[/<id>], /sector-options], overview, screener, stocks, system, tasks}}` |
| thesis | `/thesis/`, `/thesis/<id>/[dashboard/]`, `/thesis/conversation/{start,suggest,respond,news-issues}/`, `/thesis/<id>/indicators/[<indId>/[readings/]]/[auto/]`, `/thesis/alerts/[<id>/read/]`, `/thesis/<id>/close/` |
| chainsight | `/chainsight/<symbol>`, `/chainsight/sector/<industry>`, `/chainsight/watchlist/[<id>/{alternatives, archive, expand, recheck, resolve}]` |
| validation | `/validation/<symbol>` (POST/DELETE) |
| rag | `/rag/{baskets/[<id>/[{clear, items/<itemId>, add-item, add-stock-data}]], sessions/[<id>/[messages/]], monitoring/{cache, cost, history, pricing, usage}}` |
| news | `/news/[, alerts, collection-logs, llm-usage, ml-rollback[-preview], ml-trend, neo4j-status, pipeline-health, task-timeline]` |
| stocks/admin/health | `/stocks/api/market-movers/`, `/admin/providers/status/`, `/health/` |

### E-3. `/api/v1/coach/eN/` 진입점 호출 코드: **0건**
- grep `coach/e[1-6]` 또는 `/coach/`: 매칭 0 (node_modules 제외)
- legacy view 경로 호출: 0건
- → **E1~E6 진단 진입점은 프론트엔드 미연동** (백엔드는 Slice 13 종료 시점에 6개 `/api/v1/coach/eN/` 단일화 완료, 프론트엔드는 미접근)

### E-4. API base URL 설정 위치

| 위치 | 내용 |
|------|------|
| `frontend/.env.local` | `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` + `NEXT_PUBLIC_USE_MOCK=false` |
| `frontend/next.config.js` `env.NEXT_PUBLIC_API_URL` | 기본값 `http://localhost:8000` |
| `frontend/lib/api/config.ts` | `process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'` |
| `frontend/lib/api/authAxios.ts` | 동일 패턴 |
| `frontend/next.config.js` `rewrites()` | `/api/v1/:path*` → `http://localhost:8000/api/v1/:path*` (dev 프록시) |

### E-5. CORS (Django)
- `django-cors-headers ^4.9.0` (pyproject), `corsheaders` INSTALLED_APPS + `CorsMiddleware`
- `CORS_ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]` (`config/settings.py:311`)
- `CORS_ALLOW_ALL_ORIGINS = os.getenv('DJANGO_CORS_ALLOW_ALL', 'False')` (기본 False)
- `CORS_ALLOW_CREDENTIALS = True`
- `CORS_ALLOW_METHODS = [DELETE, GET, OPTIONS, PATCH, POST, PUT]`

### E-6. 인증 — **JWT (access + refresh)**
- 저장: `localStorage` — keys `access_token`, `refresh_token` (`frontend/lib/api/authAxios.ts:13~29` `tokenUtils`)
- refresh: 401 응답 시 `axios.post('${API_URL}/users/jwt/refresh/', { refresh })` 자동 (`authAxios.ts:107`)
- 컨텍스트: `frontend/contexts/AuthContext.tsx` (login/signup/logout/refreshToken 노출, `authAxios` import)
- 부수: `js-cookie ^3.0.5` 의존성 명시 있으나 tokenUtils는 localStorage 단일 소스

---

## F. 서빙·배포

- **Django는 React 빌드 산출물을 서빙하지 않음**:
  - `STATIC_URL = 'static/'` (`config/settings.py:299`) — 다른 STATIC_ROOT/STATICFILES_DIRS 없음
  - `TEMPLATES.DIRS = [BASE_DIR / 'templates']` (line 230) — `templates/` 안엔 Django admin 템플릿(`admin/sec_pipeline/`)만
  - whitenoise: settings.py grep 0
- **별도 프로세스 운영**:
  - Next.js dev → localhost:3000
  - Django → localhost:8000
  - 개발 시 `next.config.js rewrites()`가 `/api/v1/*` 프록시
- **Docker 인프라 정의**:
  - `docker/Dockerfile.frontend` 멀티스테이지 (`node:20-alpine`, `npm ci` → `npm run build` → standalone copy → `node server.js`), `EXPOSE 3000`, `HOSTNAME="0.0.0.0"`
  - `docker/docker-compose.yml`: frontend 서비스 `ports: "3000:3000"`, `NEXT_PUBLIC_API_URL=http://backend:8000`
  - `docker/docker-compose.prod.yml`: frontend `expose: "3000"`, `container_name: stockvis-frontend-prod` + nginx `ports: "80:80","443:443"`
  - `docker/nginx/nginx.conf`: `upstream frontend { server frontend:3000; }`, `listen 80`, `server_name localhost` (HTTPS 블록은 `your-domain.com` 자리표시자 — **주석 처리**)
- **`next.config.js` `output` 설정**: 부재 (그러나 `Dockerfile.frontend`가 `.next/standalone` 복사)
- **빌드 산출물**:
  - `frontend/.next/standalone/`: 부재
  - `frontend/build/`, `frontend/out/`, `frontend/dist/`: 모두 부재
  - `frontend/.next/`는 dev 캐시 (BUILD_ID/build/cache/dev/diagnostics/export 등)만
- **공개 호스팅 흔적**:
  - `vercel.json`, `fly.toml`, `render.yaml`, `netlify.toml`: 모두 **부재**
  - `.github/workflows/`: **디렉터리 부재** (CI/CD 워크플로 0)
  - 도메인 바인딩: `localhost` 또는 주석된 placeholder만
  - **한 줄 결론**: 공개 운영 호스팅 흔적 디스크에서 미확인 — dev/도커 정의 단계로 보임. 실제 외부 호스팅 운영 여부는 디스크 외 정보 필요 (사용자만이 확정 가능).
