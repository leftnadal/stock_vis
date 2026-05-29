# Monorepo 재배치 청사진 v1

> **목적**: 재배치 설계의 입력값(현 구조·의존·하네스 위치·영향 참조)을 사실로 수집한 청사진.
> **상태**: 조사 결과(2026-05-28). **실행 결정: 지금(2026-05-28).** Slice 18 보류·SR-1 트리거 폐기로 충돌원 0. 시점 = 즉시.
> **read-only 조사**로 본 문서 작성됨 — 본 문서 작성 외 코드·폴더·git 무변경. 실행 단계는 별도 작업으로 진행.

---

## ① 앱 인벤토리 + 의존 그래프 요약

### 1.1 Django 앱 (15개, INSTALLED_APPS 기준)

| 앱 | apps.py | 도메인 | 다른 앱이 import |
|----|--------|--------|------------------|
| `stocks` | ✅ | 주가·재무·심볼 코어 | **14 apps** (가장 많이 사용) |
| `api_request` | ❌ (helper 모듈) | 외부 API 클라이언트 | 7 apps |
| `news` | ✅ | 뉴스 수집·분류·ML | 6 apps |
| `marketpulse` | ✅ | Market Pulse v2 (거시 대시보드) | 5 apps |
| `serverless` | ✅ | Market Movers·Screener·Chain Sight v1·키워드 | 4 apps |
| `chainsight` | ✅ | Chain Sight v2 (기업 프로파일) | 4 apps |
| `users` | ✅ | 사용자·인증·Watchlist | 3 apps |
| `macro` | ✅ | 거시경제 데이터 | 3 apps |
| `rag_analysis` | ✅ | RAG 기반 LLM 분석 | 2 apps |
| `validation` | ✅ | 1차 검증 (Peer 비교) | 2 apps |
| `metrics` | ✅ | 공유 지표 메타데이터 | 1 app |
| `sec_pipeline` | ✅ | SEC EDGAR 10-K 파이프라인 | 1 app |
| `graph_analysis` | ✅ | 그래프 온톨로지 (모델만, API 미구현) | **0** |
| `thesis` | ✅ | Thesis Control | **0** |
| `portfolio` | ✅ | Portfolio Coach | **0** |
| `iron_trading` | ✅ | 외부 봇 read-only API | **0** |

> 보조: `api_request/`는 apps.py 없는 helper 모듈이지만 7 apps가 사용하므로 인벤토리에 포함.

### 1.2 의존 그래프 핵심 패턴

**"광범위하게 import되는" 앱 (= shared/packages 후보)**:
- `stocks` (14) ★ — 모든 도메인의 종목 데이터 소스
- `api_request` (7) — 외부 API 클라이언트 (FMP, Alpha Vantage 등)
- `news` (6) — 뉴스가 다른 도메인 입력으로 광범위 사용
- `marketpulse` (5) — 모델·시리즈가 외부에서 참조됨 (도메인+공유 혼합)
- `users` (3) — 인증 표준

**"독립 도메인" (= apps/services 후보, 다른 앱이 0 import)**:
- `thesis`, `portfolio`, `iron_trading`, `graph_analysis`

**"중간" (소수 사용, 도메인성 강함)**:
- `serverless` (4), `chainsight` (4), `rag_analysis` (2), `validation` (2), `metrics` (1), `sec_pipeline` (1)

---

## ② 분류 경계 확정 — 세션 충돌 경계 기준 (2026-05-28 재정의)

> **근본 목적**: monorepo = 세션 간 git 충돌 방지. 세션 3종 = 메인 / 서브 / 봇 연계.
> 폴더는 **세션 소유권이 겹치지 않게 분리**. DECISIONS ② 정착판.

### 정정 이력 — 이전 ②의 오류 3건 교정

1. **marketpulse를 dashboard에 통합** → **취소**. `market_pulse` 독립 apps 트랙 (둘 다 거시지만 별개 메인 트랙)
2. **apps/web (frontend 독립 트랙)** → **취소**. 공유 UI 레이어 (`packages/web/` 또는 루트 유지)
3. **iron_trading = apps 후보** → **integrations/ 격리 확정** (봇 연계 세션, read-only contract)

### apps/ — 메인 세션 (각 단독 트랙)

| 앱 | 근거 |
|----|------|
| `apps/dashboard` | 거시 통합 뷰 — 단독 메인 트랙 |
| `apps/market_pulse` (← `marketpulse` v2 본체 + `macro` v1 진입점·전용자산) | Market Pulse 본체. `dashboard`와 분리 — 둘 다 거시지만 별개 메인 트랙(베이스만 공유). v1+v2 통합 (macro views/urls/tasks + `EconomicIndicator`·`IndicatorValue` 흡수) |
| `apps/chain_sight` (← `chainsight` 진입점) | 발견/검증/가설 UI. `graph_analysis` 흡수 안 함 (services 독립) |
| `apps/portfolio` (← `portfolio` + `thesis` scope 통합) | 보유 관리 + 코치. thesis `scope` 분기 `macro/stock/holding` 흡수 |

### integrations/ — 봇 연계 세션

| 앱 | 근거 |
|----|------|
| `integrations/iron_trading` | read-only provider, contract 기반 비공유 연계. **apps/services 아님**. 가중합 **C(integrations) 5.0** > A(apps) 3.20 > B(services) 2.35 |

### packages/shared/ — 공유 인프라·도메인 모델

| 앱 | 근거 |
|----|------|
| `stocks` | 14 apps 사용. 종목 모델은 모든 도메인의 베이스 |
| `users` | 인증·Watchlist 표준 |
| `api_request` | 외부 API 클라이언트 (7 apps 공통) |
| `metrics` | 공유 지표 메타데이터 — `validation`이 12회 import |
| **`macro` 공유자산** (해체 후 분배) | `MarketIndex` · `MarketIndexPrice` 모델 (stocks EOD 파이프라인 사용) + `fred_client` · `fmp_client` (thesis도 사용) |
| **`marketpulse/utils/circuit_breaker.py`** (파일 분리) | 외부 7건 재사용(stocks·serverless·rag_analysis·thesis) — 도메인 무관 인프라 |

### packages/web/ 또는 루트 유지 — UI 공유 레이어

| 앱 | 근거 |
|----|------|
| `frontend/` (Next.js 16 SPA) | 모든 apps의 공유 UI 레이어. apps/web에 두면 세션 충돌 트리거 — 공유 위치(packages/web 또는 루트)가 정합. 최종 위치는 3단계에서 세션 충돌 분석 후 결정 |

### services/ — 백엔드 도메인 서비스

| 앱 | 근거 |
|----|------|
| `news` | 6 apps 사용하지만 자체 ML·Celery 파이프라인, 도메인 본체 |
| `serverless` | Market Movers·Screener·Chain Sight v1·키워드 |
| `rag_analysis` | LLM 분석 백엔드 |
| `validation` | 1차 검증 엔진 |
| `sec_pipeline` | SEC EDGAR 파이프라인 |
| `chainsight` (BE) | Chain Sight v2 백엔드 |
| **`services/_dormant/graph_analysis`** | 0 import · API 미구현 · 활성 세션 없음. 가격 상관 도메인이라 chainsight(사업/뉴스 관계)와 별개. 미래 어느 메인 트랙이 활용 시점에 흡수 위치 재결정. 세션 충돌 위험 0(휴면 코드). 근거: `docs/chain_sight/update_v2/ROADMAP_v1.4.md` L931 "독립 유지. 겹치지 않음." 명시 |

### 메타 레이어 — 서브 세션 (루트 유지)

| 자산 | 근거 |
|------|------|
| `docs/` · `scripts/` · `PROGRESS.md` · `DECISIONS.md` · `TASKQUEUE.md` · `CLAUDE.md` · `sub_claude_md/` · `contracts/` · `shared_kb/` · `.claude/` · `HARNESS_FITNESS.md` · `WORKSPACE_ROOT.md` | 모든 세션이 참조하는 메타 자산. 위치 변경 시 광범위 갱신 비용 — 루트 유지로 세션 충돌 회피 |

### 해체(소멸)

- **`macro` 앱**: 자산을 `packages/shared` + `apps/market_pulse`로 분산. 앱 자체 소멸. v1 진입점·전용자산은 `market_pulse`로 흡수

### 삭제 후보 (사용처 0, 마이그레이션 영향 확인 후)

- `macro.EconomicEvent`
- `macro.SectorIndicatorRelation`
- `macro.IndicatorCorrelation`

### 3단계 실행 이관 미해결 (실 코드 정독 후 판정)

1. `macro/services/macro_service.py` 위치 (packages vs services) — marketpulse v2 비즈니스 로직 분리도 코드 정독 후
2. macro v1 API 10개 deprecate 범위 — frontend 실사용 grep 후
3. 삭제 후보 3 model 실 제거 — `makemigrations --check` 후
4. `frontend/` 최종 위치 — `packages/web/` vs 루트 유지 (세션 충돌 분석 + import 비용 측정 후)
5. `iron_trading`이 읽는 앱 인터페이스 계약 — `integrations/` 격리하려면 contract 명시 필요

---

## ③ frontend 구조

| 항목 | 결과 |
|------|------|
| 구조 | **단일 패키지** Next.js 16.2.6 (`frontend/package.json` 1건) |
| workspaces 필드 | **부재** (monorepo 분할 안 됨) |
| 디렉토리 | 표준 Next 구조 (app/ components/ hooks/ lib/ services/ contexts/ providers/ types/ utils/ constants/) |
| **재배치 결정** | `apps/web/`으로 통째 이동. workspaces 도입은 별도 결정 (현재 1개 패키지라 도입 효익 적음) |

---

## ④ 하네스 자산 재배치 후보 위치

| 자산 | 현 위치 | 재배치 후보 | 근거 |
|------|---------|------------|------|
| `CLAUDE.md` | 루트 | **루트 유지** | 모든 에이전트의 진입 포인트 |
| `PROGRESS.md` / `DECISIONS.md` / `TASKQUEUE.md` | 루트 | **루트 유지** | 하네스 핵심, 단일 진실 소스 |
| `HARNESS_FITNESS.md` / `WORKSPACE_ROOT.md` | 루트 | **루트 유지** | 진입 표지 |
| `sub_claude_md/` (17 분할) | 루트 | `docs/harness/sub_claude_md/` 또는 **루트 유지** | CLAUDE.md 30+ 링크 — 위치 바뀌면 전수 갱신 |
| `contracts/` (5 spec) | 루트 | **루트 유지** | API 계약 단일 소스 |
| `shared_kb/` (Python 패키지) | 루트 | `packages/shared_kb/` | Python 패키지라 import 경로 영향 — 신중 |
| `.claude/agents/` (8 agents) | 루트 | **루트 유지** | 환경 의존, Claude CLI 스캔 위치 |
| `.claude/settings.json` | 루트 | **루트 유지** | 동일 |
| `docs/` (26+ 카테고리) | 루트 | **루트 유지** | 광범위 cross-link |
| `scripts/` (운영) | 루트 | **루트 유지** | LaunchAgent + `PROJECT_DIR` 하드코딩 |
| `config/` (Django) | 루트 | `services/django_config/` 또는 **루트 유지** | INSTALLED_APPS 갱신 영향 |
| `frontend/` | 루트 | `apps/web/` | Next 단일 패키지 이동 |
| `iron_trading/` | 루트 | `apps/iron_trading/` | 외부 봇 API |
| Django 앱 15 | 평면 (루트) | `services/*` + `packages/shared/*` + `apps/*` | INSTALLED_APPS 전수 갱신 |

> **원칙**: 외부 자동화(LaunchAgent, nightly_v3.sh) 의존하는 자산은 위치 변경 비용이 크므로 **루트 유지 우선**. import 경로/Python 패키지만 재배치 대상.

---

## ⑤ 깨질 참조 목록 + 수정 비용 감

### 5.1 영향 매트릭스

| 범주 | 위치 | 영향 라인 수 | 수정 패턴 |
|------|------|------------|----------|
| **Django INSTALLED_APPS** | `config/settings.py` L155~ | 15 앱 dotted-path | `'stocks'` → `'services.stocks'` 또는 `'packages.shared.stocks'` 일괄 갱신 |
| **앱 간 import** | 각 앱 `*.py` | **수백 건** (의존 매트릭스 = 80+ pairwise import) | 일괄 치환 + 테스트 |
| **마이그레이션 dependencies** | `*/migrations/*.py` | 다수 | `('stocks', '0001_initial')` 같은 참조 형식 — app_label은 변경 불필요. 안전 |
| **운영 스크립트** | `scripts/{celery-*,pg-backup}.sh` | **5건** L7~L21 `PROJECT_DIR="/Users/.../stock_vis"` | LaunchAgent label 또는 폴더명 변경 시 |
| **CLAUDE.md 링크** | `CLAUDE.md` | **30+ 라인** `[...](sub_claude_md/...)` `[...](docs/...)` | sub_claude_md/docs 위치 바뀌면 전수 갱신 |
| **sub_claude_md cross-link** | `sub_claude_md/*.md` 내부 | 다수 | docs/ 위치 영향 |
| **frontend API URL** | `frontend/.env*`, `next.config.js` | 1~2건 | 백엔드 라우팅 변경 없으면 영향 0 |
| **메모리** | `~/.claude/projects/.../memory/` (git 외부) | 다수 절대 경로 | 외부 갱신 |
| **`.github/workflows/`** | **부재** | 0 | **CI 없음 → 영향 0** ⭐ |
| **nightly 자동화** | `~/stock-vis-nightly/nightly_v3.sh` + `docs/infra/nightly_v3.sh` | 1건 sync | 환경 폴더명 영향 |

### 5.2 추정 총 비용

| 시나리오 | 영향 파일 수 | 비용 추정 |
|---------|------------|----------|
| **루트 평면 유지** (이름만 변경) | ~30 | 낮음 — INSTALLED_APPS + 일부 import |
| **`services/*` + `packages/shared/*` 분리** | ~80-120 | 중간 — import 경로 광범위 갱신, pytest 회귀 검증 비용 큼 |
| **하네스 + frontend까지 모두 이동** | ~150+ | 큼 — CLAUDE.md 링크 + sub_claude_md cross-link + 운영 스크립트 + 외부 자동화 sync |

> **CI 부재**는 **이점**: monorepo 재배치 시 GitHub Actions yaml 갱신 부담이 0. 향후 CI 도입 시점에 monorepo 구조가 정착되면 유리.

---

## ⑥ 잔존 브랜치 흡수 규모

### 6.1 활성 트랙

| brunch | 위치 | ahead | 마지막 commit | 의미 |
|--------|------|-------|--------------|------|
| `iron-trading-api` | 로컬만 | **1 commit** (`9ca8b47`) | 2026-05-26 | "docs(iron-trading): Codex 핸드오프 문서 + 실측 샘플 6종" — 활성 트랙. 외부 봇 API 관련 |

### 6.2 흡수됨 (ahead 0, 삭제 가능)

| brunch | 위치 | ahead | 비고 |
|--------|------|-------|------|
| `portfolio` | 로컬 + `origin/portfolio` | **0** | main에 흡수 완료, 잔재 brunch |

### 6.3 외부 자동화 잔재 (이전 정리 후 재생성, 별도 정리 권장)

| 패턴 | 로컬 brunch 수 | 비고 |
|------|--------------|------|
| `chore/dead-code-cleanup` | 1 | 외부 자동화 |
| `fix/{broken-tests, fe-type-safety, ts-compile-errors}` | 3 | 외부 자동화 |
| `test/{fe-thesis-components, fe-validation-chainsight, rag-analysis-unit-tests, sec-pipeline-tests*, users-unit-tests, validation-unit-tests}` | 9 | 외부 자동화 + 일자별 `*-20260519~21` 3건 |
| **소계** | **13건** | #71 사건의 재발 흔적 |

### 6.4 원격 잔존

| ref | 비고 |
|------|------|
| `origin/chore/cleanup-2026-05-14` | 외부 자동화 잔재 (5/14 일자) |
| `origin/portfolio` | 6.2와 동일, 삭제 가능 |

### 6.5 메모리 stale 발견

- `feature/watchlist-and-docs` — 메모리(`MEMORY.md`)와 PROGRESS에 "보존" 표기되어 있으나 **로컬·원격 모두 부재** (`git for-each-ref` 빈 출력). 메모리 갱신 필요

### 6.6 monorepo 재배치 전 권고

- **iron-trading-api 1 commit**: 별도 결정 (외부 봇 트랙이라 main 흡수 vs 별도 유지)
- **portfolio brunch 2건 (로컬+원격)**: ahead 0 → 삭제 안전
- **자동화 잔재 14건 (로컬 13 + 원격 1)**: monorepo 재배치 작업이 브랜치 위에서 진행될 가능성 높아, 그 전에 일괄 정리 권장 (Slice 17 closing 패턴 재적용)
- **메모리 stale**: `feature/watchlist-and-docs` 표기 제거

---

## 7. 다음 결정 후보 (실행 결정 시점 입력)

본 청사진을 실행 결정 입력으로 사용할 때:

1. **분류 결정**: ② 분류 초안의 packages/services/apps 경계가 적절한가? `graph_analysis` 흡수 / `marketpulse` 위치 (shared vs services vs apps) 가 핵심 갈림길
2. **하네스 자산 위치**: ④의 "루트 유지 우선" 원칙을 유지할지 vs `packages/shared/docs/`로 통합할지
3. **이름 변경 범위**: `'stocks'` → `'services.stocks'` 식의 dotted-path 갱신 비용을 감수할지 vs `services/` 디렉토리 안의 평면 `stocks/` (Django app_label은 유지)
4. **실행 트리거**: **해소 — 트리거 폐기, 지금 실행 확정**. SR-1 트리거 폐기(2026-05-28) + Slice 18 사용자 보류로 충돌원 0. 본 청사진 마감 직후 재배치 실행 단계 진입
5. **잔존 brunch 정리 선행**: ⑥의 자동화 잔재 14건을 monorepo 재배치 직전에 일괄 정리할지

---

## 참조 1차 소스

| 자산 | 경로 |
|------|------|
| Django settings (INSTALLED_APPS) | `config/settings.py` |
| 의존 매트릭스 측정 | 본 문서 STEP 2 (재현: 각 앱 디렉토리에서 `from <other_app>` grep) |
| SR-1 보류 결정 | `DECISIONS.md` "서비스 리모델링 (보류 — 2026-05-28)" |
| 서비스 리모델링 설계 (참고) | `docs/stock_vis_service_remodeling/stock_vis_service_remodeling_plan_v1(260404).md` |
| 운영 스크립트 경로 | `scripts/celery-*.sh`, `scripts/pg-backup.sh` |
| 하네스 종합 | `CLAUDE.md` "Harness Protocol" |
| 정합성 결정 | `DECISIONS.md` "문서·git 정합성 관리 원칙" 결정 1~5 |
