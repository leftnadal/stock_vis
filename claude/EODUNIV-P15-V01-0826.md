# EODUNIV-P15-V01-0826 — 실행 보고

> 지시서: DIRECTIVE-MON-EODUNIV-P15-V01-0826
> 브랜치: `monorepo/sess-univ-p15-v01` · 베이스: `d636563088e813977a8c87dbfb0d6d95a4badd94` (origin/main 절단, 2026-08-26)
> 격리: worktree `/Users/byeongjinjeong/worktrees/sv-univ-p15-v01`
> 배포 게이트: **커밋·push·main ff까지만 자율.** 워커 재시작·FE 빌드·PART A-3 prod 소급 실행·A-5 뉴스 백필 write = 사용자 명시 '배포 승인' 후 병진 절차.

---

## PART 0 — 계류 확인 2건 (읽기·보고만)

### 0.1 SWAP-V0 배포 동반 착지 커밋 중 자체 배포 게이트 대기 레인
범위 `5b03754b..686c0b7e` (swap FE 커밋 → RB-1 백-어노)를 실측한 결과, 이 구간은 **swap 전용 커밋이 아니라 다수 무관 트랙이 인터리브 착지**한 구간이다. 자체 배포 게이트(병진 수동)가 걸린 레인 후보:

| 레인 | 커밋 | 게이트 성격 |
|------|------|------------|
| NEO4J-CLOSE-1 (P2 launchd plist·runbook) | `a8336db1`, `be594bd9`, `150f86cf` | **launchd plist 변경 = 병진 수동**(H §H 승격 제외) |
| CS-P5-FE-CARD (마인드맵 카드 FE) | `ab7a449d`, `f1e04e38`(Merge, D-DEPLOY-NONFF) | FE 빌드 반영 게이트 |
| RB-1 DEPLOY-RUNBOOK (런타임 고아 감지 자동화) | `4f044d40`, `686c0b7e` | ops 자동화 랜딩 동기 규약 |

→ 통지·처분은 사용자 몫. 본 보고는 좌표 목록화까지만.

### 0.2 `/monitor/[id]/swap` 라우트 신설 재량 미신고 경위 (1줄)
해당 라우트는 **SWAP-REVIEW v0 FE 옴니버스 커밋 `5b03754b` 안에 하위 정적 세그먼트로 번들**되어 착지했다. `page.tsx` 주석이 "신규 최상위 라우트·신규 [id] 동적 세그먼트 아님 — 기존 [id] 재사용"으로 스스로 비자명성을 낮춰 프레이밍한 정황상, 라우트 신설이 **독립 라우팅 결정이 아니라 승인된 SWAP-V0 FE 스펙의 구현 디테일로 취급되어 하위 에이전트 단계 신고가 누수**된 것으로 판단된다.

---

## PART A — EOD-UNIV 재정의판 (BE)

### A-1 선행 확인 — DailyPrice 이력 심도 실측 (read-only)
감시 등록 stock-scope 모니터 = **6종**: GEV·GOOGL·PLTR(SP500) + IONQ·IREN·TLN(비SP500 타겟).

| 심볼 | DailyPrice n | 기간 | EODSignal n | SP500 active |
|------|-------------|------|-------------|--------------|
| GEV | 605 | 2024-03-27~2026-08-25 | 85 | ✅ |
| GOOGL | 786 | 2023-07-10~2026-08-25 | 69 | ✅ |
| PLTR | 786 | 2023-07-10~2026-08-25 | 85 | ✅ |
| **IONQ** | **285** | **2025-07-03~2026-08-25** | **0** | ❌ |
| **IREN** | **285** | **2025-07-03~2026-08-25** | **0** | ❌ |
| **TLN** | **285** | **2025-07-03~2026-08-25** | **0** | ❌ |

**판정**: 3종 타겟의 DailyPrice 285행은 9개 지표 전 요구치를 **전부 충족**한다 — 최대 요구는 momentum_12_1·high_52w_proximity의 `min_n=252` (285 ≥ 252). 따라서 **DailyPrice 백필 불필요**. 유일한 결손은 **EODSignal n=0** (비SP500라 EOD 파이프라인 유니버스에서 제외됨). 3종 EODSignal-파생 지표(eod_composite·change_percent·dollar_volume, 각 min_n=1)만 소스 부재로 탈락 → 현재 **6/9**. A-2(유니버스 확장)로 EODSignal이 생성되면 3종 복원 → **9/9**.

> 주: 디렉터 문서의 "6종×9지표"의 9 = **advisor 지표 카탈로그 9종**(`apps/monitor/catalog.py`)이지 EODSignal의 14시그널이 아님. 6종 = 위 6개 모니터 심볼.

### A-2 유니버스 규약 (커밋 `7ec24c62`)
- `packages/shared/stocks/services/eod_signal_calculator.py`: 신규 `eod_universe_symbols()` = SP500 active ∪ `Monitor(scope="stock").target_ref`(신규 감시등록 자동 편입, 하드코딩 없음). 감시등록 심볼 중 Stock+DailyPrice 없는 것은 조용히 스킵. SP500 순서/구성 보존. `calculate_batch`/`_load_price_data`에 additive `symbols` 파라미터(기본 None=union).
- `packages/shared/stocks/services/eod_pipeline.py`: 커버리지 분모를 `SP500Constituent.count()` → `len(eod_universe_symbols())`로 교체(`_stage_ingest`·`_build_market_summary`). 응답 키명(`sp500_universe`·`stock_universe`)은 소비자 호환 위해 유지, 값만 union.
- **증빙(read-only ORM)**: union = 506종(503 SP500 + IONQ·IREN·TLN). 6개 stock-scope 모니터 전부 편입 확인. 신규 등록 자동 반영.

### A-3 소급 재계산 (관리 커맨드 — 미실행, 배포 게이트)
- 신규 `packages/shared/stocks/management/commands/backfill_eod_signals_universe.py`. **dry-run 기본**·`--commit` 명시 시에만 write. 멱등((symbol,date) 기존 스킵).
- **feasibility**: `calculate_batch(target_date, symbols=)`가 임의 as-of + 심볼 스코프를 additive로 지원 → **계산기 재설계 없이 전체 히스토리 소급 가능**(Stage1/3/4 재사용 + `_stage_db_upsert` 재사용; Stage5 뉴스/Stage7 bake/Stage8 accuracy 생략).
- **문서화된 한계**: 날짜별 계산을 [대상종목 ∪ SPY]로 스코프 축소 → relation 시그널 S1/S2는 진짜 섹터 피어 부재로 비활성 근사(S4는 SPY 포함으로 회피). advisor가 쓰는 3필드(composite/change_pct/dollar_vol)와 나머지 11시그널은 무영향(행 존재만으로 min_n=1 충족). ⚠️ 일일 경로(A-2)는 전체 union 안에서 계산되므로 S1/S2 정상 — degeneracy는 백필 커맨드 한정.
- **dry-run 실측**: 대상 `IONQ,IREN,TLN`·범위 `2025-07-03~2026-08-25`·결측 855쌍(285×3)·기존 0.
- ⚠️ **첫 병진 `--commit` 시 검증 권고**: tagger 출력(list[dict])→`_stage_db_upsert`(list[dict]·news_context 기본 {}) 시그니처 정합 확인함. Stage5 스킵이 upsert 필수필드 누락을 유발하지 않음은 파이프라인 테스트(80 pass)로 방증되나, 첫 실행은 좁은 날짜 범위로 스모크 후 전체 실행 권장.

### A-4 검증 (9/9 매트릭스, read-only)
`source_row_count()`(`indicator_scorer.py:118`)는 `EODSignal.count()`(행 존재)만 확인(signal_count>0 불요) → 백필 1행이면 min_n=1 파생 3종 즉시 충분. DailyPrice 6종은 285행으로 이미 충족(max min_n=252). **결론: 3종 타겟 9/9 달성 경로 확증**(A-2 일일 경로 점등 + A-3 소급). 실제 매트릭스 렌더는 배포 후 첫 브리핑에서 문면 확인(검수 ⑹).
- **테스트**: `packages/shared/stocks/`(30)·stocks unit(181)·EOD 핵심 4파일(80) 전부 PASS. `makemigrations --check` = No changes(마이그 무발생).

### A-5 뉴스 백필 (조건부) — 커버리지 확인 완료·백필 write는 게이트
**시험 호출(read-only, 저장 없음)** — `FMPNewsProvider.fetch_company_news`(순수 fetch, DB 미접촉)로 3종 실측:

| 심볼 | 반환 기사 | 범위 | 프리미엄 402 |
|------|----------|------|-------------|
| IONQ | 50 (limit 도달) | 2026-08-06~08-25 | 없음 |
| IREN | 50 (limit 도달) | 2026-07-22~08-25 | 없음 |
| TLN | 38 | 2026-05-26~08-24 | 없음 |

→ **커버리지 확인**(3종 모두 FMP 뉴스 존재·프리미엄 제약 #23 무해). **그러나 실제 백필 = 공유 prod DB write** → D-DEV-PROD-SHARED-DB(shell write=자율 금지·병진 수동) + 배포 승인 원칙에 따라 **A-3과 동형으로 게이트 처리**(자율 미실행). 기존 수집 경로 `aggregator.fetch_and_save_company_news_fmp(symbol)` / task `collect_sp500_news_fmp_batch([...])`가 병진 실행 수단. limit=50 상한이라 전 구간 백필은 페이지네이션/일자 분할 필요(첫 실행 시 조정) — 강행 안 함.

---

## PART B — P1.5 숫자 표시 규약 '가' (커밋 FE `d956da60` · BE `06ddda7c`)

### B-FE 단일 포맷 유틸 (`frontend/utils/formatters.ts`)
규약 '가' 5함수 신설(기존 export 무접촉): `formatPctRule`(2자리·반올림0→부호제거 "0.00%")·`formatPrice`(2자리+통화기호+천단위·compact K/M/B 1자리)·`formatScore`(3자리 고정·-0 정규화)·`dirArrow`(반올림0→기호 생략)·`formatIndicator`(2자리). 전부 NaN/null 가드→"—".

**전 monitor 표면 적용**(타입 기반): SlimStrip(점수 3자리·delta ▲▼+3자리·`+0.00` 자기모순 삭제·손절여유 2자리·지표값 2자리·PriceLadder 통화 스레딩)·SnapshotEntry·PriceLadder(존 pct + band/tick 가격 통화)·CloseModal·AlertRow·MonitorListCard·SideColumn(평가손익 2자리 signed)·HoldGauge·`app/monitor/[id]/page.tsx`(pnl/score/매입가 통화)·`new/page.tsx`(손익비 ratio 제외). **증빙**: `-0.00`·`▲0.00`·3/2자리 병존·bare 가격 전 표면 소멸(vitest 22 신규 규약 테스트 + 기존 4파일 정밀도 갱신).
- 알려진 갭(범위 밖): `OpenEntry.tsx`의 OpenPayload는 currency_code 미전달 → USD 기본(일지 계약 확장은 별건). 통화코드 choices=USD/KRW 2종.

### B-BE 통화 소스 (하드코딩 금지)
- `MonitorSerializer.currency_code`(신규): `target_ref` 배후 `Stock.currency`(단일 소스·choices)·비주식/미매칭 "USD" 폴백. FE가 소비.
- **브리핑 프롬프트 통화 교정**(`advisor_briefing.py`): 하드코딩 "원"은 원래 없었고 **가격이 통화 단위 없이 출력**되어 LLM이 "원"으로 기본 표기하던 구조. `_fmt_price`로 통화 접두만 부착(**숫자 원문·정밀도 보존 = v1.1 수치 인용 계약 무변**) + "통화 표기" 프롬프트 라인 + 시스템 규칙("원" 치환 금지). `PROMPT_VERSION v1.1→v1.2`(문면 변경 추적·기존 substring 계약 무충돌 확인).

---

## PART C — SWAP v0.1 소수리 (커밋 FE `d956da60` · BE `06ddda7c`)

1. **판단 불가 카드 근거 관리 CTA** (SideColumn) — `judgment-unavailable-evidence-cta` 버튼→`EvidenceModal`(claim+monitorId 존재 시).
2. **상세 스트립 근거 배지 + 진입 버튼** (`[id]/page.tsx`) — `strip-evidence-badge`("근거 alive/total")·`strip-evidence-cta`→기존 `setEvidenceClaim` 재사용(최하단 기존 링크 유지). `useEvidenceStatus`+`summarizeEvidenceStatus`.
3. **임계 z 안내 문구** (EvidenceForm) — `evidence-threshold-help`: "임계는 원값이 아니라 z-점수 기준…".
4. **P-1 후보 성과 서버 계산** (SwapHoldLogSerializer + FE) — `hold/candidate_performance_pct` = held_at 스냅샷 종가(latest_close as_of) 대비 최신 종가 변화율. 새 시세 API 없음·null-safe·뷰셋 select_related. FE는 최초 로그의 BE 값 우선 소비(undefined면 Wallet 폴백) → 후보 미보유라도 DailyPrice 있으면 "현재가 데이터 없음" 소멸.

---

## 검증 (전 게이트 충족)
| 게이트 | 기준 | 실측 |
|--------|------|------|
| pytest (monitor) | ≥322 | **335** (apps/monitor+tests/monitor) |
| pytest (통합 회귀) | 회귀 0 | **546 passed / 0 fail** (+tests/unit/stocks+packages/shared/stocks) |
| tsc | 0 | **0** |
| vitest | ≥972 | **1104** (146파일, +32 신규) |
| 마이그레이션 | 무발생 | PART A/B/C 전부 `makemigrations --check`=No changes |
| 브리핑 수치 계약 | 무변 | `_fmt_price` 접두만·숫자 원문 보존·기존 substring 무충돌 |

## 배포 실행 (✅ 완료 2026-08-27 — 사용자 배포 승인 후 CC 대행, 단계별 게이트)
> ⚠️ **A-3/A-4 예측 정정 (Stage⑴ 게이트가 포착)**: EODSignal 백필**만으로는 9/9 불가**. advisor는 EODSignal-파생 3종을 **IndicatorReading robust-Z**(`score_indicator_from_model`, readings≥5)로 채점 — EODSignal 행을 직접 안 읽음. `source_row_count`(EODSignal 존재) 게이트는 **bounded 지표에만** 적용. 따라서 **`ingest_readings`(EODSignal→IndicatorReading)까지** 해야 충분(일일 refresh도 매일 수행). TLN Stage⑴에서 6/9 발견→이식 후 9/9 확인→사용자 승인으로 IONQ/IREN 동형 진행.

- **⑴ TLN**: EODSignal 백필 286행 → S1/S2 degeneracy 문서대로 확증(발화 0/0·S4=1) → 6/9 발견 → `ingest_readings --days 120`(83 readings×3) → **9/9 확정**.
- **⑵ IONQ·IREN**: EODSignal 백필 572행(286×2) + 이식(83×3 각) → **각 9/9**. 뉴스 백필(FMP days=120): TLN 29·IONQ 41·IREN 38 저장(108). (경미: FMP `published_at` naive datetime 경고 — 기존 provider 동작·저장 정상.)
- **⑶ 배포**: `worker_sync.sh`(3트리 9e2e98f3→**418b2a8e** re-detach + celery-worker/beat/daphne kickstart·inspect ping✓·daphne 401✓) + FE prod 빌드(sv-web-runtime/frontend·node v22.19.0·성공) + `com.stockvis.web-frontend` kickstart(:3000 **200**). 런타임 트리에 내 코드 실증(eod_universe_symbols·v1.2·formatPctRule). ET 03:05(beat 창 회피).
- **✅ 6×9 매트릭스 = 54/54** (TLN·IONQ·IREN 각 9/9 DB 실측 + SP500 3종 기존 9/9).
- **⑷ 익일 브리핑 TLN "지표 9/9"·통화($) 문면 = 사용자 관찰** (남은 유일 항목).
- ⚠️ 배포는 현 origin/main(418b2a8e) 전체를 반영 — 타 세션 병합분(SCAN-B2-FE·EVT·INC-P16-1 등) 동반 배포(런타임=origin/main 추적 모델, #67).

<details><summary>구 "배포 게이트 대기" 블록 (해소됨 → 위 실행으로 대체)</summary>

### (원 대기 블록 — RESOLVED @배포 2026-08-27)
커밋·push·main ff까지만 자율 수행. **아래는 승인 후 병진 절차**:
1. **PART A-3 소급 재계산 prod 실행** — `python manage.py backfill_eod_signals_universe --symbols IONQ,IREN,TLN --commit` (855행, 첫 실행 좁은 범위 스모크 권장).
2. **A-5 뉴스 백필** — 커버리지 확인됨·write는 병진(수집 태스크/aggregator).
3. **FE 빌드 반영**(:3000 prod 번들) + **워커 재시작**(v1.2 프롬프트·유니버스 union 일일 경로 점등).
4. 배포 후 검수 ⑹: 익일 브리핑에서 TLN "지표 9/9" 문면 확인(사용자 관찰).

</details>

## DECISIONS 흡수 대상 (관리 세션 반영용)
- **D-EODUNIV-UNIVERSE**: EOD 시그널 유니버스 = SP500 active ∪ Monitor(scope=stock) — 신규 감시등록 자동 편입, 하드코딩 금지. 단일 소스 `eod_universe_symbols()`.
- **D-EODUNIV-BACKFILL-SCOPE**: 백필 커맨드는 심볼 스코프 축소로 S1/S2 degeneracy(문서화)·일일 경로는 full union이라 정상.
- **D-P15-FORMAT-TYPE-BASED**: monitor 숫자 표기 = 타입 기반 단일 유틸(`utils/formatters.ts`) 경유. -0.00·▲0.00·정밀도 병존 금지.
- **D-BRIEFING-CURRENCY-V1.2**: 브리핑 가격 통화 접두(Stock.currency)·PROMPT_VERSION v1.2·수치 인용 계약 무변.
- **A-5/A-3 write = 게이트**: 공유 prod DB write는 D-DEV-PROD-SHARED-DB로 병진 수동. (본 건은 사용자 배포 승인 후 CC 대행으로 집행 완료.)
- **★common-bugs 흡수 권고 — advisor 9/9 = IndicatorReading 이식**: EOD 유니버스 확장 + EODSignal 백필만으론 9/9 불가. advisor는 EODSignal-파생 3종을 `score_indicator_from_model`(IndicatorReading robust-Z·readings≥5)로 채점하고 `source_row_count` 게이트는 bounded 지표에만 적용 → `ingest_readings`(EODSignal→IndicatorReading)까지 필수. 검증은 카탈로그 대조가 아니라 실제 `build_context` 경로로. (memory: lesson_advisor_coverage_needs_indicatorreading_ingest)

