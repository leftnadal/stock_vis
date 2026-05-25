═══════════════════════════════════════════════════════════════
[audits/2026-05_nextjs_security_exposure.md] Next.js 보안 노출 감사 (read-only)
═══════════════════════════════════════════════════════════════

## 메타

| 항목 | 값 |
|------|----|
| 일자 | 2026-05-22 |
| 조사 시점 Next.js | **16.0.0** (lockfile 해석) — C-1 분기 base |
| 입력원 | `npm audit --json`, `npm ls`, `grep`, `next.config.js` 직독 |
| 비용 | $0 |
| 후속 슬라이스 | [C-1](../slices/c1_frontend_hotfix.md) (next 16.2.6 비파괴 업그레이드) |

---

## A. 실제 설치된 버전 (lockfile 해석)

| 패키지 | resolved | 비고 |
|--------|----------|------|
| next | **16.0.0** | `node_modules/next` → `next-16.0.0.tgz` |
| react | **19.2.0** | |
| react-dom | **19.2.0** | |
| `react-server-dom-*` (webpack/turbopack/parcel) | **부재** | lockfile + `npm ls --all` 매칭 0 |

`npm audit --json` 중 react/react-dom 항목: **0건**. next/그 외는 §A-1 / §A-2 참조.

### A-1. next 22 advisory (next 16.0.0, isDirect=true, fixAvailable=16.2.6 / isSemVerMajor=false)

| advisory ID | sev | CVSS | 제목 | 취약 범위 |
|-------------|-----|------|------|----------|
| GHSA-9qr9-h5gf-34mp (1111368) | **critical** | **10.0** | RCE in React flight protocol | >=16.0.0-canary.0 <16.0.7 |
| GHSA-mwv6-3258-q52c (1111383) | high | 7.5 | DoS with Server Components | >=16.0.0-beta.0 <16.0.9 |
| GHSA-h25m-26qc-wcjf (1112646) | high | 7.5 | HTTP request deserialization DoS (insecure RSC) | >=16.0.0-beta.0 <16.0.11 |
| GHSA-w37m-7fhw-fmv9 (1111374) | moderate | 5.3 | Server Actions Source Code Exposure | >=16.0.0-beta.0 <16.0.9 |
| GHSA-9g9p-9gw9-jx7f (1112592) | moderate | 5.9 | self-hosted DoS via Image Optimizer remotePatterns | >=15.6.0-canary.0 <16.1.5 |
| GHSA-ggv3-7p47-pfv8 (1114898) | moderate | 0 | HTTP request smuggling in rewrites | >=16.0.0-beta.0 <16.1.7 |
| GHSA-3x4c-7xq6-9pq8 (1114941) | moderate | 0 | Unbounded next/image disk cache growth | >=16.0.0-beta.0 <16.1.7 |
| GHSA-5f7q-jpqc-wp7h (1116305) | moderate | 5.9 | Unbounded memory via PPR Resume endpoint | >=16.0.0-beta.0 <16.1.5 |
| GHSA-q4gf-8mx6-v5v3 (1116375) | high | 7.5 | DoS with Server Components | >=16.0.0-beta.0 <16.2.3 |
| GHSA-8h8q-6873-q5fj (1117930) | high | 7.5 | DoS with Server Components | >=16.0.0 <16.2.5 |
| **GHSA-26hh-7cqf-hhc6 (1118938)** | **high** | 7.5 | Middleware/Proxy bypass via segment-prefetch (incomplete fix) | **>=16.0.0 <16.2.6** |
| GHSA-3g8h-86w9-wvmq (1118941) | low | 3.7 | Middleware/Proxy redirect cache poisoning | >=16.0.0 <16.2.5 |
| GHSA-ffhc-5mcf-pf4q (1118943) | moderate | 4.7 | XSS in App Router with CSP nonces | >=16.0.0 <16.2.5 |
| GHSA-vfv6-92ff-j949 (1118945) | low | 3.7 | Cache poisoning via RSC cache-busting collision | >=16.0.0 <16.2.5 |
| GHSA-gx5p-jg67-6x7h (1118947) | moderate | 6.1 | XSS in beforeInteractive scripts | >=16.0.0 <16.2.5 |
| GHSA-mg66-mrh9-m8jx (1118949) | high | 7.5 | DoS via connection exhaustion (Cache Components) | >=16.0.0 <16.2.5 |
| GHSA-h64f-5h5j-jqjh (1118951) | moderate | 5.9 | DoS in Image Optimization API | >=16.0.0 <16.2.5 |
| GHSA-c4j6-fc7j-m34r (1118953) | high | 8.6 | SSRF via WebSocket upgrades | >=16.0.0 <16.2.5 |
| GHSA-492v-c6pp-mqqv (1118955) | high | 8.1 | Middleware/Proxy bypass via dynamic route param injection | >=16.0.0 <16.2.5 |
| GHSA-wfc6-r584-vfw7 (1118957) | moderate | 5.4 | Cache poisoning in RSC responses | >=16.0.0 <16.2.5 |
| GHSA-267c-6grr-h53f (1118959) | high | 7.5 | Middleware/Proxy bypass via segment-prefetch routes | >=16.0.0 <16.2.5 |
| GHSA-36qx-fr4f-26g5 (1118961) | high | 7.5 | Middleware/Proxy bypass in Pages Router i18n | >=16.0.0 <16.2.5 |

---

## B. 2026-05 권고 코드 실사용 점검

| # | 권고 항목 | 실사용 | 확인 경로 |
|---|----------|--------|----------|
| 1 | 미들웨어 / 프록시 인가 | **없음** | `frontend/middleware.ts(.js)`, `frontend/proxy.ts(.js)` 부재 |
| 2 | Server Actions (`'use server'`) | **없음** | grep `"use server"` / `'use server'`: src `.ts`/`.tsx` 매칭 0 (node_modules 제외) |
| 3 | `next/image` 사용 | **있음 (2 파일)** | `frontend/components/news/NewsDetailModal.tsx`, `frontend/components/news/NewsCard.tsx` |
| 3-1 | `next.config.js` `images` 설정 | **있음** | `images.remotePatterns`: `{protocol:'http', hostname:'localhost'}`, `{protocol:'https', hostname:'**'}` — 호스트 와일드카드 `**` |
| 4 | CSP nonce | **없음** | src `.ts`/`.tsx` nonce 매칭 0. `.next/server`/`static` 매칭은 Next 빌드 캐시 내부 |
| 4-1 | `next.config.js headers()` 내 CSP | **없음** | `headers()`에 `Content-Security-Policy` 헤더 부재. `Access-Control-Allow-{Credentials, Origin: *, Methods, Headers}`만 설정 |
| 5 | Cache Components / PPR / experimental | **없음** | `next.config.js`에 `experimental`, `cacheComponents`, `ppr`, `partialPrerendering` 매칭 0 |
| 6 | `beforeInteractive` 스크립트 | **없음** | grep `beforeInteractive`: 매칭 0 |
| 6-1 | `next/script` 사용 | **없음** | grep `from 'next/script'`: 매칭 0 |
| 7 | Pages Router 사용 | **없음** | `frontend/pages/` 디렉터리 부재. App Router(`frontend/app/`) **단독** |

---

## C. 배포 노출

| 항목 | 상태 |
|------|------|
| `vercel.json`, `fly.toml`, `render.yaml`, `netlify.toml` | 모두 **부재** |
| `.github/workflows/` | **디렉터리 부재** (CI/CD 워크플로 0) |
| `docker/Dockerfile.frontend` | 존재 — `node:20-alpine` 멀티스테이지, `EXPOSE 3000`, `HOSTNAME="0.0.0.0"` |
| `docker/docker-compose.yml` | frontend: `ports: "3000:3000"`, `NEXT_PUBLIC_API_URL=http://backend:8000` |
| `docker/docker-compose.prod.yml` | frontend `expose: "3000"` + nginx `ports: "80:80","443:443"` |
| `docker/nginx/nginx.conf` | `upstream frontend { server frontend:3000; }`, `listen 80`, `server_name localhost` (HTTPS 블록 `your-domain.com` 자리표시자, **주석 처리**) |
| `next.config.js` `output` 설정 | 부재 (Dockerfile은 `.next/standalone` 복사) |
| 호스트/포트 바인딩 | Dockerfile `ENV PORT=3000`, `ENV HOSTNAME="0.0.0.0"` |
| `frontend/.next/standalone/`, `frontend/{build, out, dist}/` | **모두 부재** (production 빌드 산출물 미디스크) |

**한 줄 결론**: 도커 컴포즈 + nginx 배포 인프라 정의는 존재(prod yaml + Dockerfile), 실제 공개 도메인 바인딩은 `localhost`/주석된 placeholder, 현 디스크에 production 빌드 산출물 부재 — **공개 운영 호스팅 여부는 디스크 외 정보 필요 (확인 불가)**.

---

## D. 업그레이드 범위 사전 가늠 (변경 없음)

- 패치 대상: `16.0.0` → **`16.2.6`** = **16.x 메이저 내 마이너+패치 범위** (npm audit `fixAvailable.isSemVerMajor=false`)
- `next.config.js` 옵션 (조사 시점 인용):
  - `devIndicators.buildActivity: true` (line 54)
  - `devIndicators.buildActivityPosition: 'bottom-right'` (line 55)
  - `images.remotePatterns`: `[{protocol:'http', hostname:'localhost', port:'', pathname:'/**'}, {protocol:'https', hostname:'**', pathname:'/**'}]` (line 37~50) — 호스트 와일드카드 `**` 포함
  - `rewrites()`: `/api/v1/:path*` → `http://localhost:8000/api/v1/:path*` (line 6~13)
  - `typescript.ignoreBuildErrors: false` (line 61)
  - `env.NEXT_PUBLIC_API_URL` (line 31~33)
- `frontend/package.json` 표기 (next/react/react-dom): **exact pin 3건** (caret 없음)

### D-1. C-1 이후 사후 검증 (참고)
- C-1 closing에서 next 16.0.0 → 16.2.6 적용 후 npm audit critical 1 → 0 / 22 advisory 모두 해소 확인 (자세히는 [c1_frontend_hotfix.md](../slices/c1_frontend_hotfix.md) 참조).
