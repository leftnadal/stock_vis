# 전진 후보 + baseline red 인벤토리 (지시서⑭ read-only 조사)

- **작성**: 2026-07-13
- **성격**: read-only 정적 분석 + 테스트 판정 재현 + repo 독해. **코드·테스트·설정 변경 0.**
- **worktree**: `monorepo/sess-forward-survey` (origin/main `bcccdb1` 기반 pristine 체크아웃 — stale `services/_dormant/graph_analysis` 잔재 **없음** 확인)
- **HALT 조건(프로덕션 영향 정황)**: 미발동. 측정은 전부 `config.settings_test`(격리 test DB) + read-only 쿼리.

---

## STEP 0 — 실측 컨텍스트

| 항목 | 값 |
|------|-----|
| origin/main tip | `bcccdb1` (docs(mgmt): MGMT-D2-DESTALE) |
| ⑬ EVENTGROUP-WINDOW 머지 여부 | **미머지** — 브랜치 `monorepo/sess-eventgroup-window` tip `fc97683`, origin/main 조상 아님. window_days 실적용은 land 대기 |
| 조사 worktree | `/Users/byeongjinjeong/Desktop/sess-forward-survey` (신규, origin/main 기반) |

**하류 항목 1차 소스**: `TASKQUEUE.md`(CS-P2-* 92~95), `DECISIONS.md`(3741 BOUNDARY-LLM 실행완료, 3752 "하류 C3(CS-P2-LLM/A3·A4) 미착수"), `docs/harness/boundary_llm_survey_2026-07-13.md`(A-3 §30~33, C3 행 §79). **`DIRECTIONS.md`는 repo에 부재.**

---

## Part A — C3 하류 후보 pick-list (라벨 중복 해소)

### A-0. "C3 하류" 정의와 A3/A4 라벨 충돌의 정체

- "C3"는 **boundary_llm 서베이의 전진표 행 라벨**(survey §79)이자 DECISIONS 3752의 축약 — EventGroup/BOUNDARY-LLM **코어 의존이 해소되어 착수 가능해진 하류 트랙 묶음**을 가리킨다. 그 자체가 슬라이스 ID가 아니다.
- **A3/A4는 repo에서 단일 로드맵 ID로 확정 불가** — 서베이 §33이 이미 "A3/A4 라벨이 dashboard EOD 시그널·audit·portfolio 등 다수 맥락에 중복, 정확한 매핑은 발주자 로드맵 대조 필요"로 명시. 본 조사가 **전 충돌처를 열거**하여 해소한다:

| 라벨 | 맥락 | 출처 | 현 상태 | "C3 하류"와 관련성 |
|------|------|------|---------|-------------------|
| **A3 / A4 (EOD 신호)** | 변동성 조정 수익률(간이 샤프) / 캔들 패턴(ta-lib) | `docs/dashboard_plan/proposal/EOD_data_analysis_plan.md:130-131` | 미구현(신호 후보, advisor review = Phase 3 권장) | **★ 가장 유력** — "A3/A4⑴ LLM-fill"의 대상. 신규 EOD 신호 + 서사 LLM-fill |
| MP1.5-A3 / A3-TAIL | 도넛 라벨 겹침(`ConcentrationDetail.tsx`) | TASKQUEUE 341, DECISIONS | ✅ 완료(`77847ca`) | 무관(marketpulse FE) |
| MP1-A3-sep | Snapshot 마이그레이션 3분리 | TASKQUEUE 366 | 🔴 HALT/DORMANT(파괴적) | 무관(marketpulse 마이그) |
| portfolio A3 | 위임 프롬프트 / 마이그레이션 분리 | DECISIONS | 이력 | 무관(coach) |
| audit A3/A4 | Celery retry / FMP chord·neo4j queue | `docs/nightly_auto_system/reports/*` | 이력(감사 항목) | 무관(infra 감사) |

> **해소 결론**: "C3 하류"의 실행 대상은 **① CS-P2-LLM(확정 슬라이스)** + **② A3/A4 = EOD 대시보드 신호(변동성조정수익률·캔들패턴) + LLM-fill 서사**(유력하나 발주자 로드맵 확인 필요). 나머지 A3/A4 라벨은 전부 무관(완료/DORMANT/이력).

### A-1. pick-list (발주자 1개 선택)

| # | 후보 | 정의 | 선행 의존 | 무엇을 여는가(가치) | 예상 규모 | 추천 재료 |
|---|------|------|-----------|--------------------|-----------|-----------|
| **1** | **CS-P2-LLM** | chain_sight Phase 2 LLM 묶음: LLM 레이어 통합 / **10-K 관계추출** / **FRED 해석** (TASKQUEUE 92) | ✅ 충족 — `packages/shared/llm` 코어 landed(`8be3f65`). 과거 블록(BOUNDARY-LLM ①) 해소됨 | 공급망/거시 관계를 **LLM으로 자동 추출** → Chain Sight 해자(관계 밀도)·거시 서사 품질 직접 상승 | **대(大)** — 3개 하위(레이어통합/10-K/FRED). 슬라이스 분할 필요 | 해자 직결·의존 이미 해소·복수 세션. **깊이 우선이면 1순위** |
| **2** | **CS-P2-GRAPH** | 그래프 화면 정제 — redesign v1 캔버스 위 EventGroup 반영(시각화) | 독립. ⑬ window_days(입력 품질)가 **선행 편입 권장**(survey §109) | EventGroup을 **사용자에게 시각적으로** 노출 → ⑬ 희석 개선의 UX 수확 | 중(中) — FE 중심 | ⑬ 직후 UX 가시화. **눈에 보이는 성과 우선이면 유력** |
| **3** | **A3/A4 (EOD 신호)** | 변동성조정수익률·캔들패턴 신호 신설 + LLM-fill 서사 | LLM 코어 해소됨. ta-lib 도입 필요(캔들) | 대시보드 신호 다양성 확대(우등생/반전 캔들) | 중(中) — 신호 2종 + 서사 | advisor review "Phase 3 권장"(우선순위 낮게 평가됨). **로드맵 확인 후** |
| **4** | **CS-M3** | Path Watchlist — 코어-위성 경로 추적 | 독립(EventGroup 위) | 코어-위성 **경로**를 사용자가 추적 → Chain Sight 탐색 심화 | 중~대 | 신규 사용자 기능. 독립 |
| **5** | **CS-P2-13F** | 13F 버그 + CUSIP 매핑 수정 (위성 `cohold_institutions` 정확도) | 독립 | 위성 confidence 신호 정확도 교정(품질 부채) | 소~중 | 버그성 부채. 기능 확장 아님 |

- **의존 그래프 요약**: CS-P2-LLM만 과거 게이트(BOUNDARY-LLM) 존재 → **해소 확인됨**. 나머지 4개는 독립. ⑬(window_days)은 CS-P2-GRAPH의 입력 품질 선행 권장이나 하드 의존 아님.
- **추천 순위 재료**(판단은 발주자): 해자·깊이 = **CS-P2-LLM**, 가시성·⑬연계 = **CS-P2-GRAPH**, 부채상환 = CS-P2-13F.

---

## Part B — baseline red 인벤토리 (47건)

### B-0. 측정 방법

- pristine worktree(origin/main `bcccdb1`) + `config.settings_test`.
- **핵심 변수 = `FMP_API_KEY` 유무**: `load_dotenv(override=False)`라 셸에 `FMP_API_KEY=""` 주입 시 키 부재 재현.
- 47 = **FMP 34 + chainsight 13** (지시서 수치와 정확 일치 재현).

### B-1. 클러스터별 분류표

| # | 클러스터 | 파일 | 건수 | 근본 원인(실측) | 게이트 조건 | 분류 |
|---|---------|------|------|----------------|-------------|------|
| 1 | chain_sight (FMP) | `tests/serverless/test_chain_sight_service.py` | **13 E** | `ValueError: FMP_API_KEY is required` (provider 인스턴스화) | **키 부재 시에만** | **(ⅰ) env-독립화** |
| 2 | enhanced_screener | `tests/serverless/test_enhanced_screener_service.py` | **12 E** | 동일 (`FMP_API_KEY is required`) | 키 부재 시에만 | **(ⅰ) env-독립화** |
| 3 | provider_factory | `tests/integration/test_provider_factory.py` | **9 F** | 동일 (factory가 빈 키 거부) | 키 부재 시에만 | **(ⅰ) env-독립화** |
| 4 | attention | `tests/chainsight/test_attention.py` | **6 F** | 3× 빈 랭킹 assert(`'SEMICON' in []`) + 3× `404==200`. **구 `theme_tags` 시드**(line 282 `theme_tags=[theme]`)인데 보드는 EventGroup 소비 → 미스매치 | 키 **무관**(항상 실패) | **(ⅱ) 전환·계약 stale** |
| 5 | leadership_api | `tests/chainsight/test_leadership_api.py` | **7 F** | 1× `404==200` + 2× `KeyError 'stocks'` + 4× `KeyError 'window'`. 동일 theme_tags 시드(line 71) + EventGroup 랭킹 응답에 `window`/`stocks` 키 부재(구 계약) | 키 무관 | **(ⅱ) 전환·계약 stale** |

**합계 = 34(ⅰ) + 13(ⅱ) = 47.** (ⅲ)실결함 = **0건.**

### B-2. 분류 근거 (판단 아닌 기준)

- **(ⅰ) env-독립화 상환 = 34건**: 전부 `ValueError: FMP_API_KEY is required`. **키 존재(.env 실키 또는 더미) 시 34건 전건 통과**(실측: 5파일 키존재 = 0 fail). 프로덕션 코드 정상(운영은 키 보유). LLM 무관(PROGRESS 445 버킷 c). → 테스트 환경 의존이지 코드 결함 아님.
- **(ⅱ) 전환·계약 stale = 13건**: 키 존재/부재 무관하게 실패(비-env). **pristine 재현**(stale `_dormant` 오탐 아님 — 과거 메모리의 "stale 잔재 오탐" 가설은 pristine에서 **반증**됨). 라우트는 **등록됨**(`events/<theme>/stocks/` → `EventRankingView`) → 404는 뷰가 theme_tags-시드를 EventGroup에서 못 찾은 결과. 두 파일 모두 **폐기 예정 theme_tags 보드 계약**을 시드·기대(CS-EG6 = "옛 theme_tags 그룹핑 디프리케이션" 대상). 프로덕션은 EventGroup+플래그로 정상 → 런타임 결함 아님, **테스트 계약 staleness**.
- **(ⅲ) 실결함 = 0건**: 34는 키로, 13은 EventGroup 시드/플래그로 각각 정상 경로 존재. 프로덕션 행위 결함 정황 없음.

> **라벨 정정**: DEBT-TEST-CHAINSIGHT(TASKQUEUE 189)의 "test_upward_learning 1f"는 **stale** — T-3b 랜딩(`3a3e921`) 후 현재 **통과**. chainsight red는 attention 6 + leadership_api 7 = **13**(upward 제외)으로 확정. "chain_sight 13e(FMP)"와 "chainsight 13(계약)"은 **동명 다른 집합**(전자=serverless FMP 에러, 후자=chainsight assertion) — 라벨 중복 주의.

### B-3. 클린 green 복원 규모 + 위험

| 클러스터 | 규모 | 위험 | 접근 |
|---------|------|------|------|
| FMP 34 (ⅰ) | **소(小)** — conftest autouse 픽스처 1개로 테스트 env에 더미 `FMP_API_KEY` 주입(또는 각 파일 `env_fmp` 적용) | **낮음** — 단, "키 부재→ValueError" 계약을 **명시 검증하는 테스트가 있으면 보존** 필요(전량 일괄 setenv 시 그 계약 테스트가 무력화). 사전 grep 필수 | 전역 더미키 or provider mock. LLM·프로덕션 무접촉 |
| chainsight 13 (ⅱ) | **중(中)** — 파일 2개 재작성 or 은퇴. theme_tags 시드→EventGroup 시드+`CHAINSIGHT_GROUP_SOURCE` 플래그 + 응답계약(`window`/`stocks` 키) 재정합 | **중** — theme_tags→EventGroup **전환 경계**를 건드림. 성급한 은퇴는 실회귀 은폐 위험. CS-EG6(파괴적 디프리케이션)의 disposition에 종속 → **@qa+@backend 판단 필요**(DEBT-TEST-CHAINSIGHT 소유) | 택1: (a) EventGroup 계약으로 재작성(지금) / (b) theme_tags 은퇴 시점(CS-EG6)까지 skip-mark |

- **총 규모**: FMP 34 = 반나절급 단일 슬라이스(저위험). chainsight 13 = 별도 판단 슬라이스(전환 계약 종속). 두 클러스터는 **독립**이라 분리 상환 가능.
- **주의**: 47은 지시서 정의 범위. 과거 LLM seam debt(125e, PROGRESS 445)는 ⑫ C2로 **종결**(DECISIONS 3749), upward_learning(+1)은 T-3b로 통과 → 47이 현재 정확 수치.

---

## 요약

- **Part A**: "C3 하류" = CS-P2-LLM(확정) + A3/A4(=EOD 신호, 유력·로드맵 확인 필요). A3/A4 라벨 5중 충돌 해소. pick-list 5종(추천 재료: 깊이=CS-P2-LLM / 가시성=CS-P2-GRAPH).
- **Part B**: 47 = 34 env-의존(FMP키, 전건 (ⅰ)) + 13 계약-stale(theme_tags→EventGroup, 전건 (ⅱ)). **실결함 0.** 복원: FMP=소/저위험, chainsight=중/전환-종속.
- **변경 0**: 코드·테스트·설정 무접촉. 본 문서만 추가.
