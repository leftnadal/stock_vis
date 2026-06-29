# stock_vis 전수 조사 보고서 (2026-06-26)

> 방향 **B 확정** ("1인 투자 무기 우선 + 다중 사용자 이음새 보존") 기준 분류 조사.
> **READ-ONLY** — 코드/문서/DB 무수정. 5개 청크 병렬 조사관(문서·데이터·코어앱·지원앱·프론트/파이프라인) 산출 통합.
> 근거 = 파일경로:라인 / 모델·함수명. 라이브 DB(PostgreSQL/Neo4j/Redis) 미조회 → 행수·노드수는 선행 감사 `docs/audit_out/differentiation_dd_2026-06-17.md` 인용, 재검증 안 함.
> 택소노미: PROTECT(해자)·KEEP-CORE(코어루프)·PROMOTE(보강필요)·SEAM-OK·SEAM-DEBT·FREEZE(외피동결)·CUT?(죽은코드)·REHOME(재배치)·DRIFT(문서불일치).

---

## A. 분류 요약표 (전 항목)

### A-1. 데이터 레이어 / 해자 (PROTECT 중심)

| 영역 | 항목 | 주분류 | 보조태그 | 근거(경로:라인) | 한줄 사유 |
|---|---|---|---|---|---|
| 데이터 | `RelationConfidence` (truth/market 이원 + 5단계 status) | PROTECT | [PROMOTE] | `apps/chain_sight/models/relation_discovery.py:64-183` | 해자 핵심. status 진화 + neo4j_dirty 단일소스. `investment_relevance` 미연결 |
| 데이터 | `CoMentionEdge` (뉴스 동시출현) | PROTECT | — | `relation_discovery.py:12-33` | 해자 입력 누적자산 (market 증거) |
| 데이터 | `PriceCoMovement` (90d 상관) | PROTECT | — | `relation_discovery.py:36-61` | 해자 입력 (market 증거) |
| 데이터 | Neo4j 그래프 (997노드 / ~13.4k엣지) | PROTECT | — | `apps/chain_sight/graph/repository.py`, `services/neo4j_sync.py:22-77` | 해자 소비층. confirmed/probable 엣지만 투영 |
| 코어앱 | Attention/Leadership 스코어링 (M1/M2) | PROTECT | [개인특화] | `apps/chain_sight/services/attention_service.py:4-22`, `leadership_compute.py` | 점수엔진(DD C1). FE 소비 부분(M7 0.67) |
| 데이터 | `CompanyChainProfile` (4-layer 집약) | KEEP-CORE | — | `apps/chain_sight/models/chain_profile.py:5-91` | 프로파일 OneToOne(Stock), 전역 |
| 데이터 | `SeedSnapshot` (시드 영속화) | KEEP-CORE | — | `apps/chain_sight/models/seed_snapshot.py` | 버그#27 대응 DB영속+Redis폴백. 전역 |
| 데이터 | chainsight 보조 4-layer (sensitivity/growth/capital_dna/insider/revenue/narrative) | KEEP-CORE | — | `apps/chain_sight/models/*.py` | 프로파일 집약 소스. 전역 |
| 데이터 | `CircuitBreaker` (Redis 상태) | KEEP-CORE | — | `packages/shared/api_request/circuit_breaker.py:35-181` | DD A6 신뢰성장치. `cb:*` 네임스페이스 |

### A-2. 코어 투자 루프 백엔드 앱

| 영역 | 항목 | 주분류 | 보조태그 | 근거(경로:라인) | 한줄 사유 |
|---|---|---|---|---|---|
| 코어앱 | `apps/chain_sight` (앱 전체) | PROTECT | [SEAM-DEBT] | `models/relation_discovery.py:64-183`, `models/saved_path.py:21-26` | 해자 본체 + 발견·관심추적 동시 탑재 |
| 코어앱 | └ seed_selection (발견 입구) | KEEP-CORE | — | `services/seed_selection.py:21,75-314` | 일일 시드 20개 = 발견 입구 |
| 코어앱 | └ SavedPath/PathAction (관심추적) | KEEP-CORE | [SEAM-DEBT] | `models/saved_path.py:21-26` (user nullable "MVP 단일사용자") | watchlist — 뷰는 IsAuthenticated 방어됨 |
| 코어앱 | └ EventGroup 클러스터링 | KEEP-CORE | — | `models/event_group.py:14-90`, `services/event_group_pipeline.py:26-33` | core-satellite jaccard 군집 |
| 코어앱 | `services/serverless` (앱 전체) | KEEP-CORE | [REHOME][개인특화] | `models.py`, `views.py` | 발견(Movers/Screener/ChainSight v1) 다발 |
| 코어앱 | └ Chain Sight v1 (ETF/LLM관계/13F) | KEEP-CORE | [DRIFT] | `services/llm_relation_extractor.py:96-502`, `models.py:855-1282` | apps/chain_sight v2와 **이중 구현** |
| 코어앱 | └ Screener / Market Movers | KEEP-CORE | [SEAM-OK] | `models.py:330-512,4-108`, `views.py` | 발견 단계 |
| 코어앱 | `services/validation` (1차검증) | KEEP-CORE | [SEAM-DEBT] | `tasks.py:158-178`, `models/peer_preset.py` | 1차검증 단계 (DD D3 0.83), **주간 배치** |
| 코어앱 | └ `PeerPreset` (6프리셋) | KEEP-CORE | [SEAM-DEBT] | `models/peer_preset.py:5-46` (user FK 없음) | 프리셋 전역 — 사용자 소유 아님 |
| 코어앱 | └ `UserPeerPreference` (커스텀) | SEAM-OK | — | `models/peer_preset.py:48-79` (user FK) | 사용자 오버레이 정상 |
| 코어앱 | `macro/` (v2 데이터 레이어) | REHOME | [KEEP-CORE][SEAM N/A] | models-only, `apps/market_pulse/*` 17곳 import | 모델만 top-level, 로직은 apps/ — 분산 |
| 코어앱 | `apps/market_pulse` (v2) | KEEP-CORE | [SEAM-OK][개인특화] | `models/regime.py`, `regime/rules.yaml` | 거시맥락=발견 전 프레이밍 |
| 코어앱 | `apps/portfolio` (Coach) | PROTECT | [SEAM-OK][개인특화] | `models.py:53-57,761,858` (user FK 전수) | 포트폴리오=루프 종착, 완전 user-scoped |

### A-3. 지원/파이프라인 백엔드 앱

| 영역 | 항목 | 주분류 | 보조태그 | 근거(경로:라인) | 한줄 사유 |
|---|---|---|---|---|---|
| 지원앱 | `packages/shared/stocks` | PROTECT | KEEP-CORE | `models.py:653-725`(DailyPrice/재무), `config/urls.py:37` | 주가·재무 = 전 앱 데이터 토대 |
| 지원앱 | `packages/shared/users` | KEEP-CORE | [SEAM-DEBT] | `urls.py:10-26`(JWT+legacy 이중), `models.py:12` | 인증·Watchlist·Portfolio 코어. 이중 인증경로 부채 |
| 외피 | └ 오픈 회원가입 `JWTSignUpView` | FREEZE | — | `jwt_views.py:52-129` (AllowAny, ~77줄) | 자율가입 = 외피, 1인용엔 불필요 |
| 외피 | └ 공개 프로필 `PublicUser` (@username) | FREEZE | — | `views.py:114-126`, `urls.py` `@<user_name>/` | 멀티유저/소셜 외피 |
| 지원앱 | `packages/shared/metrics` | KEEP-CORE | — | `models/*.py`, `tasks.py:25,117` | 공유 지표 메타+벤치마크, 내부서비스(urls 없음) |
| 지원앱 | `services/news` (Intelligence v3) | PROTECT | — | `tasks.py:104→733`, `services/news_neo4j_sync.py` | 뉴스이벤트/관계 → 해자 기여 |
| 지원앱 | `services/sec_pipeline` (SEC EDGAR) | PROTECT | — | `tasks.py:338`(seed_relations_to_chainsight), `:397` | 10-K 공급망 → RelationConfidence 직접 공급 |
| 지원앱 | `services/rag_analysis` | KEEP-CORE | [SEAM-OK] | `models.py:14`(user FK), `views.py` 전건 IsAuthenticated | DataBasket LLM 분석, 사용자 스코프 |
| 지원앱 | `thesis` (가설 통제실 코어) | KEEP-CORE | [SEAM-OK] | `views/thesis_views.py:42-53`(get_queryset filter user) | 빌더+관제실 활성, 모범 스코프 |
| 휴면 | └ thesis `InvestorDNA` (C4) | REHOME | [DRIFT] | `models/learning.py:97`, `thesis_views.py:303`(write만) | 집계 write만, read API 부재 — 반휴면 |
| 휴면 | └ thesis `ValidityRecord/HypothesisEvent` (C3) | REHOME | [DRIFT] | `models/learning.py:7,55`, `thesis_views.py:99,114` | close 시 기록되나 서빙 엔드포인트 없음 |
| 외피 | └ thesis `community.py` | FREEZE | [CUT?] | `models/community.py:1-45`, admin.py만 참조 | ThesisFollow/PopularThesisCache=소셜 외피, 완전 휴면 |
| 외부 | `integrations/iron_trading` | SEAM-OK | [SEAM-DEBT] | `views.py:32,67`(AllowAny), `urls.py` | 외부봇 read-only 계약. 무인증이 부채 |
| 휴면 | `services/_dormant/graph_analysis` | REHOME | — | `settings.py:198`(migrations만), urls 미등록, import 0건 | 상관관계 엔진, 완전 휴면 |
| 잔재 | 루트 `rag_analysis/` `sec_pipeline/` `validation/` | CUT? | [DRIFT] | 비-pyc 파일 0건 (`__pycache__`/빈 migrations만) | monorepo 이전 후 빈 껍데기 |

### A-4. 프론트엔드 + 파이프라인

| 영역 | 항목 | 주분류 | 보조태그 | 근거(경로:라인) | 한줄 사유 |
|---|---|---|---|---|---|
| 프론트 | `/` (루트=EOD Dashboard) | PROTECT | — | `app/page.tsx:6-29` `useEODDashboard` | 일일 루프 발견 진입점 |
| 프론트 | `/chainsight/[symbol]` (에고 그래프) | PROTECT | — | `app/chainsight/[symbol]/page.tsx:1-45` ForceGraph2D | 연쇄 발견 핵심 워크스페이스(해자 UI) |
| 프론트 | `/chainsight` (이벤트 보드) | PROTECT | — | `app/chainsight/events/page.tsx` | 발견 루프 보드 |
| 프론트 | `/chainsight/watchlist` (Path Watchlist) | PROTECT | — | `app/chainsight/watchlist/page.tsx:1-19` `usePathWatchlist` | 관심추적(Node Monitoring) |
| 프론트 | `lib/api/authAxios.ts` | PROTECT | — | `authAxios.ts:1-60` tokenUtils 단일소스+refresh | JWT 이음새 단일 출처 |
| 프론트 | `/portfolio` + PortfolioTable | KEEP-CORE | [SEAM-DEBT][DRIFT] | `PortfolioTable.tsx:103,143` raw fetch+수동 Bearer | 루프 종착, authAxios 우회 |
| 프론트 | `/thesis/*` (목록·빌더·관제·마감) | KEEP-CORE | — | `app/thesis/(list)/`, `[thesisId]/`, `new/` | 가설 통제실(검증 단계) |
| 프론트 | `/market-pulse-v2` | KEEP-CORE | — | `app/market-pulse-v2/page.tsx`, `lib/api/marketPulseV2.ts` | 거시 레짐/breadth(맥락) |
| 프론트 | `/coach/e1~e6` | KEEP-CORE | — | `app/coach/e1~e6/page.tsx` | Portfolio Coach 6화면 |
| 프론트 | validation client (GET) | KEEP-CORE | [SEAM-DEBT] | `services/validation.ts:19-21` (Authorization 없음, credentials:include) | 읽기에 user 스코프 미적용 |
| 프론트 | `/login` `/signup` `/mypage` | KEEP-CORE | [SEAM-OK] | `app/login`, `app/signup`, `app/mypage:10-25` | 단일 사용자라도 인증 필요(결제/구독 UI 없음) |
| 프론트 | `/dashboard` (별도 authed shell) | CUT? | [DRIFT] | `app/dashboard/page.tsx:1-30` 빈 shell | 루트 EOD와 중복 레거시 |
| 프론트 | `/market-pulse` (v1) | CUT? | [DRIFT] | `app/market-pulse/page.tsx`, `services/macroService.ts` | v2와 병존(구버전 잔존) |
| 파이프라인 | SEC EDGAR (Track A→Neo4j / B→PG) | PROTECT | — | `sec_pipeline/extractor.py:35,97`, `tasks.py:339,398` | 공급망 관계 = 해자 원천 |
| 파이프라인 | News Intelligence v3 (6단계) | PROTECT | — | `news/tasks.py:104→508→555→603→637→733` | 뉴스이벤트/관계 = 해자 기여 |
| 파이프라인 | EOD Screening (시그널+JSON Baking) | KEEP-CORE | [DRIFT] | `stocks/tasks.py:585`, `services/eod_json_baker.py`, `eod_signal_tagger.py:17-104` | 메인화면 데이터. 시그널 개수 표기 혼선 |
| 파이프라인 | market_pulse_v2 (regime/breadth/sector/conc) | KEEP-CORE | [SEAM-DEBT] | `market_pulse/tasks/*.py`, `setup_marketpulse_beat.py` | 거시 맥락. 스케줄 DB 등록 별도 |
| 인프라 | Celery beat_schedule dict | DRIFT | [SEAM-DEBT] | `config/celery.py:124-139` "런타임 무시" 주석 | dict≠DB 진실의소스 (버그 #28) |

### A-5. 문서 레이어 (드리프트 중심)

| 영역 | 항목 | 주분류 | 근거(경로:라인) | 한줄 사유 |
|---|---|---|---|---|
| 문서 | `CLAUDE.md` 앱 표 | DRIFT | vs `config/settings.py:186-219` | 플랫 경로 — monorepo 재편 미반영 |
| 문서 | `sub_claude_md/architecture.md` | DRIFT | architecture.md:24-35 vs settings.py | 앱 표 전체 옛 구조, graph_analysis "API 미구현" 오표기 |
| 문서 | `sub_claude_md/api-endpoints.md` | DRIFT | vs `config/urls.py:42-59` | chainsight v2·validation·sec·thesis·portfolio·mp v2 누락 |
| 문서 | `sub_claude_md/chain-sight.md` | DRIFT | chain-sight.md:90-109 | 파일 경로 전부 구(舊)경로 |
| 문서 | `sub_claude_md/thesis-control.md` | DRIFT | :30 (`thesis_control/`) vs `thesis/apps.py:6` | 앱명 오기 + FE-PR-3~6 "예정"(실구현됨) |
| 문서 | `sub_claude_md/common-bugs.md` | DRIFT | #31·#33 중복 부여, README "26개" vs 실제 #39 | 번호 충돌 + 카운트 stale |
| 문서 | `HARNESS_FITNESS.md` | DRIFT | :42-44 "다음 05-13"(6주 경과), §5 "Doc-Code Sync OK" 거짓 | 검증 루프가 드리프트 못 잡음 |
| 문서 | `contracts/{chainsight,validation}-api.yaml` | SEAM-OK | yaml paths == api/urls.py | 스펙↔구현 일치 ✅ (드리프트 예외) |
| 문서 | `WORKLOG.md` `FMP_API_ENDPOINTS.md` | FREEZE | Jan 수정, "PostgreSQL(예정)" | 초기 작업일지 — 역사 보존 |

---

## B. 모듈별 카드 (§3의 5질문)

### [apps/chain_sight] — 해자 본체
- **기능**: 기업 프로파일(성장단계·자본DNA·민감도) + 관계발견(뉴스동시출현/가격동조/신뢰도) + Attention/Leadership 점수 시드선정 + SavedPath 추적/Recheck + Neo4j 동기화.
- **대상**: 둘다(하이브리드) — 프로파일·관계·점수 14종은 symbol-keyed 전역, SavedPath/PathAction만 user-scoped.
- **해자기여**: **Y — 본체.** RelationConfidence 정의처(`relation_discovery.py:64-183`).
- **루프위치**: **Y — 발견(seed_selection) + 관심추적(SavedPath) + 1차검증 일부(recheck).**
- **이음새**: `SavedPath.user` nullable("MVP 단일사용자", `saved_path.py:21-31`)=SEAM-DEBT. 단 `watchlist_views.py:33,38`이 IsAuthenticated+`filter(user=request.user)` 강제(P0 #2 방어). 전역 프로파일은 N/A.
- **→ 최종: PROTECT [SEAM-DEBT]**

### [services/serverless] — Movers/Screener/Chain Sight v1
- **기능**: Market Movers(RVOL/Corp Action+AI키워드) + Screener(50+필터+테제빌더+알림) + Chain Sight v1(ETFHolding/LLMExtractedRelation/13F) + 배치 키워드.
- **대상**: 둘다 — 시장데이터 전역, ScreenerPreset(nullable=시스템), ScreenerAlert(user 필수), InvestmentThesis(nullable).
- **해자기여**: **Y** — `LLMExtractedRelation.llm_confidence_score`(`models.py:1215`) → 관계추출 신뢰도가 해자 입력.
- **루프위치**: **Y — 발견 + 관심추적(ScreenerAlert).**
- **이음새**: nullable/필수 구분은 의도적이나 익명 폴백 다수(C-1 참조). **[DRIFT]: Chain Sight v1/v2 이중 구현.**
- **→ 최종: KEEP-CORE [SEAM-DEBT][REHOME][개인특화]**

### [services/validation] — 1차 검증
- **기능**: 34지표 + 6프리셋 peer 랭킹 + 7카테고리 신호 + 벤치마크 델타 + LLM peer 필터. **주간 배치.**
- **대상**: 서비스전용 + 사용자 커스텀(UserPeerPreference per-user).
- **해자기여**: **N** — `benchmark_confidence`는 표본크기 신뢰도지 RelationConfidence 아님.
- **루프위치**: **Y — 1차검증 단계 그 자체**(스케줄은 주간).
- **이음새**: `PeerPreset` 전역=SEAM-DEBT(사용자 소유 아님), 나머지 SEAM-OK.
- **→ 최종: KEEP-CORE [SEAM-DEBT]**

### [macro/ + apps/market_pulse] — 거시 맥락
- **기능**: macro=거시 시계열 모델(models-only). apps/market_pulse=regime 5단계 분류 + breadth/sector/concentration + anomaly + LLM 브리핑/translation.
- **대상**: 서비스전용(전역). user FK 0건(NewsViewLog만 24h dedup용).
- **해자기여**: **N** — 순수 거시 분석.
- **루프위치**: 거시맥락(발견 前 프레이밍). 코어 4단계 위는 아니나 직전 컨텍스트.
- **이음새**: N/A(전역).
- **→ 최종: macro=REHOME [데이터레이어] / apps/market_pulse=KEEP-CORE [SEAM-OK][개인특화 US/한국어]**

### [apps/portfolio] — Portfolio Coach (종착)
- **기능**: LLM 진단 6단계(E1~E6 GARP/진단/코멘트/대화/조정파싱/비교) + cost guard + append-only 원장.
- **대상**: **나전용(per-user)** — Wallet/ChatSession/Decision user FK, 전 API IsAuthenticated.
- **해자기여**: **N** — RelationConfidence 참조 0건.
- **루프위치**: **Y — 포트폴리오(종착).**
- **이음새**: **SEAM-OK 전수** — 다중사용자 준비 완료.
- **→ 최종: PROTECT [SEAM-OK][개인특화 비용캡]**

### [packages/shared/{stocks,users,metrics}]
- stocks: 주가/재무 토대 → PROTECT/KEEP-CORE. users: 인증/Watchlist 코어, JWT+legacy 이중 경로=SEAM-DEBT → KEEP-CORE [SEAM-DEBT]. metrics: 내부 지표 서비스(urls 없음) → KEEP-CORE.

### [services/news, sec_pipeline, rag_analysis]
- news v3: 9모델 + ML + Neo4j sync, 해자기여 Y → PROTECT. sec_pipeline: 10-K 공급망→RelationConfidence 직접공급, 해자기여 Y → PROTECT. rag_analysis: DataBasket user-scoped, 해자기여 N → KEEP-CORE [SEAM-OK].

### [thesis] — 가설 통제실
- 코어(빌더/관제실): user FK + get_queryset 모범 스코프 → KEEP-CORE [SEAM-OK]. 휴면 하위: C3(validity)/C4(DNA)는 write만 배선·read API 부재 → REHOME. community(소셜)=admin 전용 휴면 → FREEZE [CUT?].

### [프론트엔드 발견 UI 묶음]
- `/` EOD + `/chainsight/[symbol]` 에고그래프 + `/chainsight/watchlist`: 해자 시각화 + 발견→추적 루프 UI, user 스코프(watchlist) → **PROTECT**. authAxios=JWT 이음새 단일소스 → PROTECT.

### [파이프라인 4종]
- SEC EDGAR / News v3: 해자 원천 → PROTECT. EOD Screening: 메인 데이터, 시그널 개수 표기 혼선 → KEEP-CORE [DRIFT]. market_pulse_v2: 거시맥락, 스케줄 DB 등록 이원화 → KEEP-CORE [SEAM-DEBT].

---

## C. 횡단 점검 6종 결과 (§4)

### C-1. 이음새 부채 맵 (우선순위 = 영향 × 수리난이도) — *지금 수리 안 함, 목록만*

**SEAM-OK (온전 — 보존):**
- `thesis.*` 전 모델/뷰 — **모범 사례**: `thesis/views/thesis_views.py:42,52-53`(IsAuthenticated + get_queryset filter user), `:164,209,250`(get_object_or_404 user=request.user).
- `chainsight.SavedPath` 뷰 — `apps/chain_sight/views/watchlist_views.py:33,38,69` (P0 #2 IDOR 차단 주석).
- `users.Portfolio/Watchlist` (unique_together(user,…)), `rag.DataBasket`(교차소유 검증 `:442`), `validation.UserPeerPreference`(`:91,600,618`), `market_pulse.NewsViewLog`, `apps/portfolio.*`(전수 user FK 체인).
- 프론트: `authAxios.ts`, `marketPulseV2.ts`(tokenUtils 재사용).

**SEAM-DEBT (미래 서비스화 부채):**

| 순위 | 위치 | 빠진 스코프 | 영향×난이도 |
|---|---|---|---|
| **1 (高)** | `services/serverless/views.py:1788-1817` `get_thesis` | `@permission_classes([AllowAny])` + `InvestmentThesis.objects.get(id=…)` user 검증 0 → **IDOR-read**(임의 ID 비공개 테제 열람) | 영향 高 × 난이도 S(가드 1줄) |
| **2 (高)** | `services/serverless/models.py:785-793` `InvestmentThesis.user on_delete=SET_NULL` | 사용자 삭제 시 테제 고아화 → 소유 추적 단절 | 영향 高 × 난이도 M(CASCADE 전환+마이그레이션) |
| **3 (中)** | `services/serverless/views.py:977-1002` `screener_preset_detail` GET | GET 소유자 검증 없음(PATCH/DELETE만 검증) + use_count 증가 부수효과 | 영향 中 × 난이도 S |
| **4 (中)** | `services/serverless/views.py:950,1254,1736` 생성 | AllowAny + 익명 폴백(`user=None`) → 익명 소유 데이터풀(P0 #2 잔존 패턴) | 영향 中 × 난이도 M |
| **5 (中)** | `apps/portfolio/models.py:44,215` Wallet/Portfolio | user FK 정의됐으나 **0행·뷰 미소비**(Coach는 stateless body holdings) — 이음새 정의-후-휴면 | 영향 中(M1 레버리지 잠김) × 난이도 M |
| **6 (中)** | `services/validation` `PeerPreset` | user FK 없음 — 프리셋 전역, 다중사용자 시 공유 충돌 | 영향 中 × 난이도 M |
| **7 (低)** | `apps/chain_sight/models/saved_path.py:21-28` 모델 레벨 | user `null=True`("MVP 단일사용자") — 뷰는 보강됐으나 모델 nullable 잔존 | 영향 低 × 난이도 S |
| **8 (低)** | 프론트 `PortfolioTable.tsx:103,143`, `validation.ts:19-21`, `userInterestService.ts` | raw fetch + 수동 Bearer / Authorization 누락 → refresh 미적용·읽기 익명화 (common-bugs #26 계열) | 영향 低 × 난이도 S(authAxios 이관) |
| **9 (低)** | `packages/shared/users/urls.py:10-26` | JWT(`jwt/*`) + legacy 세션(`login/`,`Users`) 병존 — 인증 경로 단일화 미완 | 영향 低 × 난이도 M |
| **10 (低)** | `integrations/iron_trading/views.py:32,67` | AllowAny — API키/throttle/IP 게이팅 전무(외부 노출 계약인데 무인증) | 영향 中(외부) × 난이도 S(키 게이트) |

**해당없음 (전역 코어 — 정상):** chain_sight 해자 일체, market_pulse 조회 뷰, validation 시스템지표, serverless 시장데이터, news 적재. ⚠ 잠재부채: `chainsight:seeds:{date}` 캐시키에 user 차원 없음 → 사용자별 개인화 필요해지면 재설계(우선순위 낮음).

### C-2. 서비스 외피 인벤토리 (전부 FREEZE — 남김+신규중단)

> **결제·구독·청구·멀티테넌트 코드 = 0건.** `stripe/billing/payment/subscription/checkout` grep 히트는 전부 SEC 비즈모델 분류 콘텐츠 또는 재무 필드명(도메인). 프론트 결제/구독/온보딩 UI도 0건. **동결할 외피는 인증/소셜 시드뿐 — 인벤토리 극소.**

| 외피 코드 | 경로:라인 | 대략 라인수 |
|---|---|---|
| 오픈 회원가입 `JWTSignUpView` | `packages/shared/users/jwt_views.py:52-129` | ~77 |
| signup 라우트 + api_root 광고 | `packages/shared/users/urls.py:10`, `config/views.py:28` | 2 |
| 공개 프로필 `PublicUser` (@username) | `packages/shared/users/views.py:114-126`, urls `@<user_name>/` | ~13 |
| 소셜 `ThesisFollow`+`PopularThesisCache` | `thesis/models/community.py:1-45` (+admin.py:8,11,81-87) | 45(+admin) |
| 프론트 `/login` `/signup` | `app/login/page.tsx`, `app/signup/page.tsx` | — (단일 사용자에도 인증 필요 → KEEP, 단 signup은 외피성) |

> User 모델에 tenant/org/role/premium 필드 전무 → 추가 동결 대상 없음.

### C-3. 하드코딩 / 개인특화 위험 ([개인특화] 태그)

**⚠️ 진성 개인 식별자 (일반화 1순위):**
- `services/serverless/tasks.py:1054` — 하드코딩 수신자 `recipients = ["goid545@naver.com", "jinie545@gmail.com"]` (운영자 본인 메일 직매립).

**점수 가중치/임계값 (도메인 튜닝값 — B에서 허용, 식별만):**
- chain_sight: `attention_service.py:4,22`(M1 가중 0.5/0.3/0.2), `:26`(`ADV_FLOOR=45,799,011` — "p5 of 652 stocks 2026-06-15" 특정시점 산출), `:212`(컷 70/20); `leadership_service.py:26`(WINDOWS/MIN_OBS); `event_group_pipeline.py:26`(HALF_LIFE 21/CORE_THR 0.2); `seed_selection.py:21`(MAX_SEED 20); `views.py:543`(min_truth 35).
- validation: `category_signal_calculator.py:22-61`(34지표 카탈로그), `:223`(신호컷 65/35); `benchmark_calculator.py:32`(사이즈버킷), `:217`(신뢰도 peer≥15); `metric_calculator.py:271`(ROIC 세율 0.21 US).
- market_pulse: `regime/rules.yaml:9-50`(NFCI≥1.0/VIX≥40 등), `anomaly/rules.yaml`, `api/status.py:34`(미국 장 9:30-16:00 ET), `constants/insights.py:20-466`(한국어 교육텍스트+가중), `briefing/prompt.py:17`(한국어 면책), `i18n/labels.py:71`(한국어 GICS↔XL*).

**심볼/URL 하드코딩 (만료·동기화 위험):**
- `services/serverless/services/etf_csv_downloader.py:59-180`(SPDR/iShares/ARK CSV 직링크 — 만료 위험), `cusip_mapper.py:100-369`(수동 매핑), 섹터→ETF 매핑 4곳 중복(`views.py:616`, `data_sync.py:26`, `sector_heatmap_service.py:36`, `theme_matching_service.py:33`).
- `macro/migrations/0004,0006`(20지수 + GICS 시드).

**LLM 모델명 하드코딩 (provider 교체 시 일괄수정):**
- `apps/portfolio/llm/client.py:43-46`(gemini-2.5-flash/claude-sonnet-4-5/haiku-4-5 + 단가), `cost_guard.py:92`(비용캡, env override 有).
- serverless 다수 `MODEL="gemini-2.5-flash"`, `regulatory_service.py:515`은 `gemini-2.0-flash-exp`(**버전 불일치**). validation `llm_peer_filter.py:80`, market_pulse `llm/client.py:24`.

> 시크릿: 전 앱 하드코딩 시크릿 **없음** — 전부 `settings.*`/`os.getenv()` 경유(정상).

### C-4. 휴면/데드 코드 (REHOME 후보)

| 항목 | 활성여부 | 재배치 제안 |
|---|---|---|
| `services/_dormant/graph_analysis` (모델 399줄+서비스 2개) | 휴면 확정 (INSTALLED_APPS는 migrations 목적, urls 미등록, import 0, beat 0) | REHOME → chainsight RelationConfidence 또는 market_pulse 흡수 검토. 보존이면 현 `_dormant` 유지 |
| thesis `InvestorDNA` (C4) | 반휴면 (write 활성 `thesis_views.py:303`, read/serve API 부재) | **REHOME → portfolio** (DNA, 힌트 일치) |
| thesis `ValidityRecord/HypothesisEvent` (C3) | 반휴면 (기록 활성, 서빙 엔드포인트 없음, 데이터 축적 중) | **REHOME → market_pulse** (validity learning, 힌트 일치) |
| thesis `community.py` | 완전 휴면 (views/urls/services 0, admin만) | FREEZE(소셜 외피) 또는 CUT?(소셜 미로드맵 시) |
| 루트 `rag_analysis/` `sec_pipeline/` `validation/` | 데드 (비-pyc 0건, PR8a 이동 잔재) | CUT? (단 migrations/ 삭제 안전성은 별도 확인) |
| 프론트 `/dashboard`, `/market-pulse` v1 | 중복 (루트 EOD / v2와 병존) | CUT? 후보 |

### C-5. 해자 생성 경로 지도 (RelationConfidence) — *끊긴 구간 = 최우선 PROMOTE*

```
[생성]                          [학습/감쇠]                  [소비]
extract_co_mentions ─┐          check_stale_and_decay        sync_dirty_relations → Neo4j
(relation_tasks:18)  │          (relation_tasks:405)         (neo4j_sync:22-57)
 CoMentionEdge       ├─► update_relation_confidence ──────►  seed_selection (get_relation_change_seeds:262)
calculate_price_     │   (relation_tasks:211-402)            api/views neighbors / sector_graph
co_movement ─────────┤   ★고정 계단함수 임계★              ↑ previous_status 추적(relation_discovery:165)
(relation_tasks:126) │   (count≥10→85 / corr≥0.8→85)
 PriceCoMovement     │
sec_pipeline/tasks ──┘   SUPPLIES_TO (truth) [부분/UNKNOWN]
```

**끊긴 구간 (PROMOTE):**
1. **`investment_relevance` write 0건** — `relation_discovery.py:112` 정의됐으나 `update_relation_confidence` 어떤 defaults도 세팅 안 함(`relation_tasks.py:303-393`). truth/market은 채워지나 **둘을 합성하는 신호가 영원히 null**. → **합성 1줄 추가 = DD ID4(truth vs market 괴리) 즉시 점화. 난이도 S.**
2. **"학습"이 감쇠 전용** — `check_stale_and_decay`는 시간기반 하향만. **증거 재확인 기반 상향(re-confirm) 피드백 루프 부재**, `last_verified_at` 미사용. → **decay↔re-confirm 양방향 루프 = DD ID16(타당성 재급유, 복리). 난이도 M.**
3. **점수 = 고정 계단함수 (≠ Robust Z)** — DD C1 "Robust Z+Decay"는 실제로 `thesis/services/indicator_scorer.py`(EOD/가설용)에만 존재. RelationConfidence는 고정임계(`relation_tasks.py:288,328,367`). → **DRIFT(자산명 불일치) + 점수정교화 여지(PROMOTE).**
4. **증거 소스 7종 중 3종만 가동** — `has_peer/industry/news/price`만 세팅. `has_supply_chain/etf/llm` 및 SUPPLIES_TO/HAS_THEME/COMPETES_WITH 미생성. sec_pipeline이 RelationConfidence 참조(grep 적중)하나 SUPPLIES_TO 생성 여부 UNKNOWN. → **SEC truth관계(DD A5 0.93) 합류 시 truth/market 이원 완성. PROMOTE.**
5. **소비 끝단 FE 부분연결** — heat/attention(M7 0.67)·status age 배지(DD ID1 0.88, 미구현) FE 미노출. **데이터 이미 존재 → 난이도 S.**

### C-6. 문서-현실 드리프트 (심각도 순)

1. **[상] monorepo 재편 전면 미반영** — CLAUDE.md 앱 표·architecture.md:24-35·api-endpoints.md·multi-agent.md:7이 플랫 경로. 실제: `settings.py:186-219`(packages/shared·services·apps·_dormant). **모든 신규 세션이 잘못된 경로로 출발.**
2. **[중] graph_analysis 휴면 이전 미반영** — 문서는 "REST API 미구현(현역)", 실제 `services._dormant.graph_analysis`(휴면).
3. **[중] 루트 빈 껍데기 3개** — `rag_analysis/`·`sec_pipeline/`·`validation/`가 0 .py 파일 잔재. 실제 코드는 `services/*`. (CUT? 후보, 혼동 유발)
4. **[중] thesis 앱명 오기** — 문서 `thesis_control/`, 실제 `thesis/`(apps.py name='thesis').
5. **[중] thesis FE-PR-3~6 상태 충돌** — completed-features.md/thesis-control.md "예정", 실제 `components/thesis/{builder,dashboard,alerts,close}` 구현됨.
6. **[중] api-endpoints.md surface 누락** — chainsight v2/validation/sec/thesis/portfolio/mp v2 라우팅 누락(`config/urls.py:42-59` 존재). contracts/는 정확 → 문서만 뒤처짐.
7. **[중] HARNESS_FITNESS 자기검증 거짓** — "Doc-Code Sync OK"가 monorepo 재편으로 무효. 6주째 미평가.
8. **[중] EOD 시그널 개수** — 코드는 ~10-14개(`eod_signal_tagger.py:17-104`), CLAUDE.md "14개", **지시문 "47 시그널"은 코드와 불일치**(출처 UNKNOWN).
9. **[중] Chain Sight 이중 구현** — 발견 로직이 `apps/chain_sight`(v2)와 `services/serverless`(v1) 분산.
10. **[하] macro 역할변경 / common-bugs 번호충돌 / beat dict↔DB 이원화** — 의도된 상태이나 문서 부재 또는 검색 모호성.
11. **양호(역드리프트 없음):** `contracts/{chainsight,validation}-api.yaml` ↔ 구현 1:1 일치(SEAM-OK).

---

## D. 전환 실행 우선순위 (B 기준)

### PROMOTE Top 10 — "내 무기를 가장 빨리 날카롭게" (영향 × 난이도)

| # | 항목 | 영향 | 난이도 | 근거 |
|---|---|---|---|---|
| 1 | `investment_relevance` 합성 1줄 추가 | 高 (truth/market 괴리 신호 점화, DD ID4) | **S** | `relation_tasks.py:303-393` defaults에 합성식 추가 |
| 2 | heat/attention·status age 배지 FE 노출 | 高 (데이터→UX 마지막 칸, DD ID1/M7) | **S** | 데이터 이미 존재, FE 소비만 |
| 3 | SEC SUPPLIES_TO(truth) → RelationConfidence 합류 | 高 (truth/market 이원 완성, DD A5 0.93) | M | `sec_pipeline/tasks.py:338` 검증 후 has_supply_chain 세팅 |
| 4 | decay↔re-confirm 양방향 학습 루프 | 高 (해자 복리, DD ID16) | M | `last_verified_at` 활성 + 상향 로직 |
| 5 | Chain Sight v1/v2 발견 입구 단일화 | 中 (이중구현 혼선 제거) | M | serverless v1 → apps/chain_sight v2 흡수 |
| 6 | RelationConfidence 점수 고정임계 → Robust-Z 정교화 | 中 (DD C1 자산명 정합 + 신호 품질) | M | `relation_tasks.py:288,328,367` |
| 7 | EdgeDiff/recheck 1차검증 연결 강화 | 中 (발견→검증 순환, DD ID14) | M | `recheck_service.py` + validation 연계 |
| 8 | ETF/LLM 소스 생성기 가동(`has_etf/llm`) | 中 (증거 소스 7종 완성) | M | 생성기 위치 UNKNOWN → 선조사 |
| 9 | LLM 모델명 버전 통일(2.0-exp → 2.5) | 低 (`regulatory_service.py:515` 불일치) | S | 단일 상수화 |
| 10 | EOD 시그널 개수 문서 정합 + 시그널 확장 | 低 (드리프트 해소 + 발견 신호 증강) | S | tagger 정의 vs 문서 동기화 |

### FREEZE 목록 — 지금 손 뗄 서비스 외피 (남김, 신규작업 중단)
- `JWTSignUpView`(오픈 회원가입), `PublicUser`(공개 프로필), `thesis/community.py`(소셜 팔로우/랭킹), 프론트 signup 화면. **전부 합쳐 ~150줄 미만 — 외피 규모 극소.** 결제/구독/멀티테넌트는 애초에 0건.

### SEAM-DEBT Top — 나중에 갚을 서비스화 부채 (지금은 표시만)
1. serverless `get_thesis` IDOR-read (高·S) — ⚠ 보안 관점에선 1인용이라도 즉수리 권장.
2. `InvestmentThesis SET_NULL` 고아화 (高·M).
3. screener_preset_detail GET 소유검증 (中·S).
4. AllowAny 익명 폴백 패턴 (中·M).
5. portfolio Wallet 이음새 정의-후-휴면 (中·M).
6. PeerPreset 전역 (中·M).

### REHOME / CUT? (구조 정리)
- **REHOME**: graph_analysis(_dormant 유지 or 흡수), thesis C3→market_pulse·C4→portfolio, Chain Sight v1→v2, macro/ 로직 통합.
- **CUT?(극소·명백한 죽은코드만)**: 루트 빈 껍데기 `rag_analysis/`·`sec_pipeline/`·`validation/`, 프론트 `/dashboard`·`/market-pulse` v1. (삭제 전 import/migrations 영향 별도 확인.)

---

## E. B 운영 상태 점검 (한눈 요약)

- **이음새 온전/깨짐/누락**:
  - SEAM-OK 모듈: ~7군 (thesis·chainsight watchlist 뷰·users CRUD·rag·validation 커스텀·market_pulse NewsViewLog·portfolio + 프론트 authAxios).
  - SEAM-DEBT: **10건** (serverless 4 + portfolio Wallet + validation PeerPreset + SavedPath nullable + 프론트 raw fetch + users 이중인증 + iron_trading 무인증).
  - 누락(전역으로 굳어 user 차원 없음): chainsight 캐시키·시드 — 잠재부채(낮음).
  - → **이음새는 대체로 보존됨. 코어 사용자 데이터(thesis/portfolio/rag)는 모범 스코프, 부채는 serverless·프론트 raw fetch에 집중.**

- **외피 동결 인벤토리 규모**: 파일 4~5개, **~150줄 미만**. 결제/구독/멀티테넌트 0건. → **B에서 "손 뗄 외피"가 거의 없다 = 이미 1인 도구에 수렴된 상태.**

- **해자 경로 무결성**: 생성(✅ co-mention/price/peer) → 학습(⚠ 감쇠 전용, 상향 루프 없음) → 소비(⚠ Neo4j/seed ✅, FE 부분). **5곳 끊김 — 특히 `investment_relevance` write 0건(생성 끝단 누락)과 단방향 학습(복리 미작동)이 해자를 "쌓이지만 날카로워지지 않는" 상태로 만듦.**

- **→ 지금 당장 PROMOTE 1순위**: **`investment_relevance` 합성식 1줄 추가**(`relation_tasks.py` defaults) — 난이도 S, 영향 高. 이미 채워진 truth_score·market_score를 합성해 "진실 vs 시장 괴리" 신호를 점화하면 클론이 데이터 시간으로만 따라올 수 있는 해자가 즉시 사용자 화면(heat 배지·status age, PROMOTE #2)으로 연결된다.

---

## 부록: 미확인(UNKNOWN)

- **라이브 DB 미조회** — RelationConfidence 13,574행·Neo4j ~13.4k엣지·87k 스냅샷 등 수치 전부 2026-06-17 감사 인용, 현재값·`PeriodicTask` enabled 상태 미검증.
- `services/sec_pipeline/tasks.py`의 RelationConfidence 쓰기(SUPPLIES_TO truth 생성·`has_supply_chain` 세팅) 여부 — grep 적중, 줄단위 미독.
- `has_etf_source`/`has_llm_source` 생성기 위치 (메인 relation_tasks에 없음).
- EOD "47 시그널" 출처 (코드 ~10-14개, 문서 "14개").
- chain_sight `graph/repository.py`·`schema.py` Cypher/온톨로지 상세, coach e1~e6 구현 깊이, serverless 일부 서비스(patent/regulatory/uspto) 세부.
- `docs/` 하위 30개 서브디렉토리 개별 설계서 대부분 (인덱스만 확인).
- contracts/ sec-pipeline·shared-types 재검증 (2026-04-13 이력만).
- 포트폴리오→발견 상류 환류 루프 존재 여부.
