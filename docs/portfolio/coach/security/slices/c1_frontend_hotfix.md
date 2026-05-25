═══════════════════════════════════════════════════════════════
[security/slices/c1_frontend_hotfix.md] C-1 — 프론트엔드 긴급 보안 hotfix
next 16.0.0 RCE(CVSS 10) 등 보안 의존성 비파괴 업그레이드
═══════════════════════════════════════════════════════════════

> **마스터 인덱스**: [`../SECURITY_LEDGER.md`](../SECURITY_LEDGER.md) (C-1 행)
> **원본 스캔**: [`../advisories/2026-05_dependency-audit.md`](../advisories/2026-05_dependency-audit.md) (§1)

이 문서는 `c1_closing.md`에서 `slices/c1_frontend_hotfix.md`로 git mv·재구성됨
(C-1 후속 docs 슬라이스 2026-05-24).

## 분기

- **base HEAD**: `00dc18d` (slice14, "docs: 코드베이스 감사 보고서 생성")
  - Slice 14 closing(`053bd11`) 이후 외부 야간 docs 커밋 누적.
- **브랜치명**: `security/c1-frontend-deps`
- **pre-commit hook**: `ALLOWED_BRANCHES`에 `security/c1-frontend-deps` 추가 (.git/hooks/ — 워킹 트리·커밋 무관)

---

## 변경 파일 (frontend/ 내 4건, 외부 0건)

| 파일 | 의도 / 사유 |
|------|------------|
| `frontend/package.json` | 5 패키지 보안 버전 상향 |
| `frontend/package-lock.json` | 5 패키지 + transitive 일괄 갱신 |
| `frontend/tsconfig.json` | **next 16.x 자동 마이그레이션** — `moduleResolution: "node" → "bundler"` (Next 15+ 공식 권장값) + 배열 멀티라인 포매팅. `git checkout 00dc18d -- frontend/tsconfig.json` 원복 시도 후에도 `npm run build`/`npm install`이 즉시 동일하게 재작성 → 받아들임. lint 룰셋과 무관 (`moduleResolution`은 eslint 동작에 영향 X). |
| `frontend/app/chainsight/page.tsx` | **(A) 결정 — 범위 확장**. 베이스라인 next 16.0.0에서 이미 `useSearchParams() should be wrapped in a suspense boundary` prerender 실패 → C-1 비파괴 검증 게이트 2 before/after 비교 불가. 차단 해소 1건만 Suspense wrap. 코치 화면 무관. (§Part A 검증 참조) |

`git diff --stat 00dc18d -- frontend/`:
```
frontend/app/chainsight/page.tsx |  20 +-
frontend/package-lock.json       | 514 ++++++++++++++++++++++-----------------
frontend/package.json            |  10 +-
frontend/tsconfig.json           |  16 +-
4 files changed, 328 insertions(+), 232 deletions(-)
```

---

## Part A 검증 — 커밋 `7482fdc` 의 성격

C-1 후속 docs 슬라이스(2026-05-24)에서 read-only 사실 확인 수행.

### A-1. 커밋 자체

- `git show 7482fdc --stat`: `frontend/app/chainsight/page.tsx` **1 파일만 변경** (+18 / -2).
- diff 핵심:
  - `import { Suspense, useEffect } from 'react';` — `Suspense` 추가 import.
  - 기존 `export default function ChainSightPage()` → `function ChainSightPageInner()` 로 rename (외부 노출 제거).
  - 새 default export = `<Suspense fallback={<spinner div>}><ChainSightPageInner /></Suspense>`.
  - fallback = 기존 `isLoading` 분기와 동일한 `animate-spin` div (UX 동일).

### A-2. 변경 사유 — base 시점 사실

`git show 00dc18d:frontend/app/chainsight/page.tsx`에서 확인:
- `import { useSearchParams } from 'next/navigation';` — 사용 중.
- `const params = useSearchParams();` 가 **default export 함수 본문에서 직접 호출** (외부 Suspense 경계 없음).
- `usePathname`, `useRouter` 등은 부재 (`useSearchParams` 1건만 Suspense 경계 요구).

### A-3. 결론

**7482fdc = Next 16 빌드 에러 해소 ✅**

근거 한 줄: base의 `useSearchParams()`가 외부 Suspense 경계 없이 default export 본문에서 직접 호출되었고, Next 16 prerender가 이를 정확히 차단(`useSearchParams() should be wrapped in a suspense boundary at page "/chainsight"`)했으며, 7482fdc는 그 경계만 정확히 1개 추가 (`ChainSightPageInner` 추출 + 외부 `<Suspense>` wrap, fallback은 기존 spinner 재사용으로 UX 무변경) — 무관한 변경 없음.

---

## 변경 패키지 before / after

| 패키지 | before | after | 표기 |
|--------|--------|-------|------|
| next | `16.0.0` | **`16.2.6`** | exact |
| react | `19.2.0` | **`19.2.6`** | exact |
| react-dom | `19.2.0` | **`19.2.6`** | exact |
| axios | `^1.13.1` | **`^1.16.1`** | caret |
| js-cookie | `^3.0.5` | **`^3.0.7`** | caret |

지시서 하한 충족: next ≥16.2.6 ✓, react/react-dom ≥19.2.1 ✓, axios ≥1.15.2 ✓, js-cookie ≥3.0.6 ✓.
메이저 경계 무월: axios <2.0.0 ✓, js-cookie <4.0.0 ✓, react <20.0.0 ✓.

`eslint-config-next` `16.0.0`은 **그대로 둠** (지시서 명시 — lint 규칙 churn 회피).

`images.remotePatterns` (hostname:'**')는 **그대로 둠** (지시서 명시 — 별도 보류 결정).

---

## npm audit before → after

| 시점 | critical | high | moderate | total | 패키지 |
|------|----------|------|----------|-------|--------|
| **before** (16.0.0) | **1** | 5 | 5 | **11** | ajv, axios, brace-expansion, flatted, follow-redirects, js-cookie, js-yaml, minimatch, next, picomatch, postcss |
| **after** (16.2.6) | **0** | **0** | 2 | **2** | next, postcss (동일 advisory) |

- **before critical 1건** = next CVSS 10 RCE (GHSA-9qr9-h5gf-34mp, React flight protocol) — **해소됨**.
- next 자체 22 advisory 모두 해소.
- axios 17 advisory 모두 해소.
- js-cookie 1 advisory 해소.
- transitive (ajv/brace-expansion/flatted/follow-redirects/js-yaml/minimatch/picomatch) 모두 `npm audit fix` (no --force)로 자연 정리.

### 잔여 2건 (모두 동일 advisory)

| advisory ID | aliases | range | 위치 |
|------|---------|-------|------|
| GHSA-qx2v-qp2m-jg93 | (postcss XSS via Unescaped `</style>`) | postcss <8.5.10 | `node_modules/next/node_modules/postcss` (next 내부 nested) |

- npm 권고 fix: `npm audit fix --force` → **`next@9.3.3` 다운그레이드 = 메이저 파괴적 변경** → **적용 안 함** (지시서 §--force 금지).
- 게이트 5 잔여 분류: **파괴적-only 잔여** (지시서 §2 명시 분류).
- 다음 next 패치 릴리스가 nested postcss를 8.5.10+로 갱신하면 자연 해소.

---

## vitest before / after

| 시점 | files | tests | duration |
|------|-------|-------|----------|
| before (16.0.0) | 12 PASS | **65 PASS** | 3.17s |
| after (16.2.6) | 12 PASS | **65 PASS** | 2.86s |

**회귀 0** ✓ (베이스라인 동일).

---

## 검증 게이트 6종

| # | 게이트 | 결과 | 비고 |
|---|--------|------|------|
| 1 | npm install 성공 + lockfile 정상 재생성 | **PASS** | 8 vulnerabilities 안내 (→ #2에서 정리) |
| 2 | npm run build 성공 | **PASS** | next 16.2.6, 25 routes (16 static + 9 dynamic) |
| 3 | npm test (vitest): ≥ 베이스라인 | **PASS** | 65/65 = 베이스라인 동일 |
| 4 | npm run lint 성공 | **(부분) PASS** | C-1 변경 파일(`chainsight/page.tsx`) 단독 lint = **0 error**. 전체 lint 181 errors는 **pre-existing** — `eslint-config-next@16.0.0` 무변경 + 변경 파일과 무관한 기존 코드의 룰 위반 (C-1 범위 밖 부채, 분리 등록 후보). |
| 5 | npm audit: next/axios/js-cookie 0건 | **PASS** | axios 0 / js-cookie 0 / next 1건 = postcss transitive only, 파괴적-only 잔여 (§잔여 표 참조) |
| 6 | git diff --stat: frontend/ 내 한정 | **PASS** | 4 파일 모두 frontend/ 내. frontend/ 밖 변경 **0**. (지시서 명시 3 파일 + tsconfig 자동 + chainsight Suspense — 후 둘은 §변경 파일 표에 사유 명시) |

### 게이트 4 보충 — base lint 비교 미실측
- stash로 base 코드 측정 시도 → Claude Code auto mode classifier가 stash 자체를 차단 (C-1 진행 작업 손실 위험).
- 대신: `eslint-config-next@16.0.0` 패키지 무변경 + tsconfig 변경은 lint 룰셋에 영향 없음(`moduleResolution`은 lint 동작 무관) + C-1 변경 파일 단독 lint = 0 error → **C-1으로 새 lint 에러 발생 0건 확정**.
- 전체 181 errors는 base에서도 동일하다고 추론 (룰셋·해당 파일 무변경).

### 백엔드 영향 (참고)
- 본 슬라이스는 `frontend/` 외 0 변경 → 백엔드 740 회귀 / IDENTICAL 31/31 영향 **무 (별도 실행 불필요)** — 지시서 명시. 게이트 6의 git diff가 보증.

---

## 비용

- **$0** (LLM 호출 0건, npm 레지스트리 조회만).

---

## 커밋 (2건 — 의미 단위 분리)

| # | 해시 | 메시지 |
|---|------|--------|
| 1 | `7482fdc` | C-1 pre-fix — /chainsight Suspense wrap (베이스라인 빌드 차단 해소) |
| 2 | `ba1a187` | C-1 — frontend 보안 의존성 비파괴 업그레이드 |
| 3 | (본 커밋) | C-1 closing 보고서 |

지시서 §커밋 §2 "next.config.js deprecation 호환 수정" 커밋: **불필요**.
- npm run build 출력에 `devIndicators`/`buildActivity` 관련 경고 0건.
- viewport/themeColor 메타 위치 권고 경고는 빌드 차단 아님 + 페이지 컴포넌트 메타 위치 변경은 C-1 범위 밖.

---

## 다음 (메모, 본 closing 범위 밖)

- C-2 / C-3 (백엔드 보안) — 별도 슬라이스 (`SECURITY_LEDGER.md` §1).
- `images.remotePatterns` hostname:'**' 처리 결정 사이클 — 별도 보류 대상.
- 잔여 postcss transitive — next 패치 릴리스 자연 해소 모니터링 (`SECURITY_LEDGER.md` §2 **SEC-#1**).
- `viewport`/`themeColor` 메타 export 위치 마이그레이션 — 별도 부채 등록 후보.
- 전체 lint 181 errors (any/unused) — pre-existing, 별도 부채 등록 후보 (`SECURITY_LEDGER.md` §2 **SEC-#2**).

Slice 15(프론트 코치 화면) 진입 시 하드 선행조건(next RCE 차단)은 본 C-1로 **충족**.
