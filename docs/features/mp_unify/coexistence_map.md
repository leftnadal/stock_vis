# MP-UNIFY-S0 — market_pulse v1/v2 공존 지도 (read-only 조사)

> 조사 세션: 2026-07-28 `monorepo/sess-MP-unify-s0`, base origin/main `2a1bd10c`. **read-only**(코드 변경 0·마이그레이션 0). 산출 = 본 보고서 + TASKQUEUE MP-UNIFY 트랙 신설. 통합 실행·결정은 이 보고를 입력으로 디렉터 사이클에서 닫는다.

---

## 0. 한 줄 결론
v1 = **macro 레거시**(`/api/v1/macro/*` + `app/market-pulse` 프론트, 라이브 FRED/FMP API 대시보드, **정식 메뉴 노출**). v2 = **`/api/v2/market-pulse/*` + `app/market-pulse-v2`**(DB 스냅샷·payload builder, **메뉴 미노출 베타**). **통합은 서빙 게이트·DB와 독립**(마이그레이션 0, worker_sync 절차 무변경) → 서빙 전 완주 가능. drift는 섹터 1건(코드 존재, 실사용 노출 0).

---

## 1. 공존 지도

### 1-a. 표면 전수표 (생사 판정)
| 표면 | 경로 | 생사 | 근거 |
|------|------|------|------|
| v1 프론트 | `frontend/app/market-pulse/page.tsx` | **(a) 실서빙** | Header.tsx:17·MobileNav.tsx:25 메뉴 링크, AuthGuard 렌더. 자동 redirect 없음(수동 v2 배너 `page.tsx:106`만) |
| v2 프론트 | `frontend/app/market-pulse-v2/` | **(a) 실서빙·베타** | 페이지·훅·API 연결 살아있음. **정식 메뉴 미노출** — v1 배너 클릭으로만 도달 |
| admin market-pulse 탭 | `AdminTabNav.tsx:22` | 별개(관리자) | v1/v2 표면과 무관 |
| Django 템플릿 | (없음) | — | market_pulse .html 0건 = 구 화면은 Django 템플릿 아님 |

### 1-b. API 전수표
**v1** = `/api/v1/macro/*` → `apps.market_pulse.urls`(namespace `macro`, `config/urls.py:39`). 뷰 = `views.py`(전부 `MacroEconomicService` 위임 실로직, FRED/FMP 라이브).

| 엔드포인트 | 뷰 | 프론트 소비 |
|-----------|-----|------------|
| `pulse/` | MarketPulseView | ✅ `hooks/useMarketPulse.ts:66` (집계 응답) |
| `sync/` (POST) | DataSyncView | ✅ useMarketPulse.ts:127 |
| `sync/status/` | SyncStatusView | ✅ useMarketPulse.ts:111 |
| `fear-greed/` | FearGreedIndexView | ❌ 무소비(래퍼만) — 단 pulse 집계 내부에서 서비스 메서드 소비 |
| `interest-rates/` | InterestRatesView | ❌ 무소비 — pulse 내부 소비 |
| `inflation/` | InflationDashboardView | ❌ 무소비 — pulse 내부 소비(economy) |
| `global-markets/` | GlobalMarketsView | ❌ 무소비 — pulse 내부 소비 |
| `calendar/` | EconomicCalendarView | ❌ 무소비 — pulse 내부 소비 |
| `vix/` | VIXView | ❌ **순수 무소비**(pulse 미포함) |
| `sectors/` | SectorPerformanceView | ❌ **순수 무소비**(pulse 미포함) |

> v1 pulse 집계 = fear_greed + interest_rates + economy(inflation) + global_markets + calendar (`macro_service.py:336`). **vix·sectors는 pulse에도 미포함** → 개별 엔드포인트+집계 모두 무소비.

**v2** = `/api/v2/market-pulse/*` → `apps.market_pulse.api.urls`(namespace `marketpulse_api_v2`, `config/urls.py:62`).

| 엔드포인트 | 뷰 | 프론트 소비 |
|-----------|-----|------------|
| `overview` | OverviewView (`views/overview.py:365`, `_build_payload`) | ✅ fetchOverview |
| `cards/<id>/detail` | CardDetailView (`views/cards.py:140`) | ✅ fetchCardDetail |
| `regime/zscore` | RegimeZScoreView (cards.py:184) | ✅ fetchRegimeZScore |
| `regime/analog` | RegimeAnalogView (cards.py:225) | ✅ fetchRegimeAnalog (C-L3 "왜?") |
| `news/refresh` (POST) | NewsRefreshView | ✅ refreshNews |
| `i18n` | I18nView | ✅ fetchI18n |
| `health` | HealthView | ❌ 무소비 |

### 1-c. 중복 로직 쌍 (같은 질문 · v1↔v2)
| 질문 | v1 소스 | v2 소스 | 판정 |
|------|---------|---------|------|
| **Regime(국면)** | 없음 (v1은 fear_greed 심리지수만, regime enum 부재) | RegimeSnapshot 계통 단일(overview/cards 소비) | **중복 아님 — v2 단일** |
| **VIX** | VIXView→라이브 FRED `get_vix`+레벨밴드 (`fred_client.py:374`) | MacroVIXProvider→macro DB `IndicatorValue(VIXCLS)` (`macro_vix_provider.py:37`) | **source-split**(v2 단독 노출 없음, 동일 payload 충돌 미발생) |
| **금리** | InterestRatesView→라이브 FRED 대시보드 | regime/inputs.py T10Y2Y/T10Y3M(DB, regime 재료) | 독립(v2에 금리 대시보드 없음)·source-split |
| **인플레** | InflationDashboardView→라이브 FRED | (없음) | **v1 전용** |
| **섹터** | SectorPerformanceView→라이브 FMP `change_percent` 정렬 (`market_pulse_client.py:254`) | `_sector_card`/`_sector_detail`→SectorFlowSnapshot(macro DB 상대강도·rank_in_universe, `overview.py:210`) | **★DRIFT**(다른 소스·계산·리더 정렬) |
| **payload 조립** | MarketPulseView→`get_market_pulse_dashboard`(라이브 flat 조립) | OverviewView→`_build_payload`(스냅샷 카드) | **복제(동일 의도)·공유 코드 0·구조 상이**(views.py:7 도크스트링 경고) |

**대상 아님(intraday 라이브, D1 Option3 잔류)**: `tasks/regime.py`·`regime/inputs.py`·`tasks/anomaly.py`·`anomaly/*`. v1/v2 중복 후보에서 제외.

---

## 2. 분류표 (DELETE / MIGRATE / FREEZE)
| 자산 | 분류 | 근거 · 소비자 |
|------|------|--------------|
| v1 `vix/`·`sectors/` 엔드포인트 | **DELETE 후보** | 개별 무소비 + pulse 집계 미포함 = 순수 무소비. 뷰·서비스 메서드 제거 시 소비자 0 |
| v1 `fear-greed/interest-rates/inflation/global-markets/calendar/` 엔드포인트 | **MIGRATE(엔드포인트만) / 서비스 유지** | 개별 엔드포인트 프론트 무소비 → 라우트 제거 가능. 단 서비스 메서드(`get_fear_greed_index` 등)는 **pulse 집계 내부 소비** → 서비스 로직 유지 |
| v1 `pulse/`·`sync/`·`sync/status/` | **FREEZE / MIGRATE(표면 결정 종속)** | 프론트 실소비. v1 표면 통합 방향(아래) 확정 전 동결 |
| v1 프론트 `app/market-pulse/page.tsx` | **FREEZE(사용자 결정)** | 정식 메뉴 노출 실서빙 표면. v2로 흡수/리다이렉트/메뉴 교체는 **제품 결정** — 조사 범위 밖 |
| v1 `MacroEconomicService`(FRED/FMP 라이브) | **MIGRATE 판단 보류** | pulse 표면이 이 서비스 위임. 표면 존치 시 유지, 폐기 시 함께 |
| v2 `health` 엔드포인트 | **FREEZE** | 프론트 무소비지만 운영 헬스체크 용도 가능(판정 불가) |
| 섹터 drift 쌍 | **통합 시 정본=v2** | v1 SectorPerformanceView = 갈라진 라이브 복제본. 정본 = v2 `_sector_card`(payload builder 원칙) |

---

## 3. 타이밍 판정 재료 (★핵심)
- **서빙 게이트 접촉면 = 0(절차 독립)**: `worker_sync.sh`는 `git checkout --detach origin/main`으로 3트리(worker/web/api) **통째 sync**(파일 지목 없음, `worker_sync.sh:138·150`). v1 자산 유무와 무관하게 동일 절차. web rebuild(next build)도 frontend 전체 빌드라 v1 page.tsx가 빠지면 빌드 대상만 감소, 절차 무변경. → **통합이 서빙 절차를 바꾸지 않음**.
- **DB 마이그레이션 = 0**: `makemigrations --dry-run` = "No changes". market_pulse 모델(RegimeSnapshot·Snapshot 3종·MarketPulseNews 등)은 **v2/intraday 공유** — v1 전용 테이블 없음. macro.models(indicators)도 v1/v2 공유 지표 소스. **v1 제거해도 마이그레이션 발생 안 함**.
- **통합 예상 규모(추정)**: 
  - 최소(엔드포인트 정리): v1 개별 무소비 엔드포인트(vix/sectors 순수 + 5개 라우트) 제거 + 테스트 정리 = **~1 세션**.
  - 표면 통합(사용자 결정 필요): v1 프론트 → v2 흡수/리다이렉트 + 메뉴 링크 교체(Header/MobileNav → v2) + pulse/sync 이관 or 폐기 = **~1~2 세션**. drift(섹터)는 v1 SectorPerformanceView 삭제로 자연 해소.
- **판정**: 통합은 서빙·DB와 **완전 독립** → **C-N-REPAIR/C-L3 서빙 경로와 무충돌, 서빙 전 완주 가능**(동결 불요). 단 v1 프론트 표면 처분은 제품 결정이라 그 결정 전엔 착수 불가.

---

## 4. drift 실측 (최우선 보고)
- **Q3 섹터 = 코드 레벨 DRIFT**: v1 `SectorPerformanceView`(라이브 FMP `change_percent` 내림차순, `market_pulse_client.py:277`) vs v2 `_sector_card`(macro DB 상대강도·`rank_in_universe` 상하위3, `overview.py:224`). 같은 "섹터 강도" 질문에 **다른 소스·계산·리더 정렬** → 동일 시점 리더 갈림 가능.
  - ⚠️ 단 **실사용 노출 0**: v1 sectors/ 프론트 무소비 + v1 pulse 집계에 섹터 미포함 → 사용자가 두 값을 동시에 보지 않음. **"대기 불가 버그" 아님**(잠재적 drift, 통합 시 v1 삭제로 해소).
- **Q2 VIX/금리 source-split**: 동일 FRED 시리즈(VIXCLS·T10Y2Y·T10Y3M)를 v1=요청시 라이브 API(밴드 처리), v2=macro DB 적재분(밴드 없음). v2 단독 노출 없어 응답 충돌 미발생, 값 시점·임계 처리만 갈림(위험 기록).

---

## 5. 미해결 질문 (read-only 한계 — 디렉터 결정 시 감안)
1. **v1 pulse 실응답 vs v2 overview 실값 비교** = 서비스 프로세스 호출 필요(§3 read-only 제약으로 금지) → 미측정. 코드 diff 수준까지만 확인.
2. **v1 표면 실트래픽**(실사용자 유무) = 접근 로그 미조회 → 메뉴 링크는 존재하나 실사용 빈도 미상.
3. **v2 정식 승격 계획**(메뉴 노출 전환 시점) = 제품 결정, 조사 범위 밖.
4. **v1 pulse/sync 표면 처분 방향**(v2 흡수 vs 리다이렉트 vs 폐기) = 제품 결정.

---

## 6. STRUCT-CLEANUP 대조 (Step 3.4)
기존 DORMANT `STRUCT-CLEANUP`(TASKQUEUE:516)은 **intraday(regime/anomaly) → dashboard 도메인 이동**(D1 보류) 트랙 — 본 조사의 **v1/v2 표면 통합과 별개 축**(intraday는 "대상 아님"으로 분류됨). 중복 아님, 병합 불요. 단 둘 다 "market_pulse 구조 정리"라는 상위 우산 아래 있음(디렉터가 통합 시 순서 조율 감안).
