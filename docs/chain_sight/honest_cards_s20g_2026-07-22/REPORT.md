# ⑳-G 관계 카드 정직화 재설계 — REPORT

- **일자**: 2026-07-22
- **세션**: 실행 세션 (⑳-F 진단 반영)
- **브랜치**: `monorepo/sess-20g-honest-cards`
- **원칙**: additive-only(기존 API 필드 불변) · 마이그레이션 0 · Neo4j 0 · 외부 API 0

---

## STEP 0 — 실측 요약

### 0-2 ★서빙 빌드 모순 판별 (⑳-F Q4 후속) — **미완결(도구 제약) + 논리 결론**

- next-server PID 25615(v16.2.6, node v22.19.0)는 확인. 그러나 **cwd 실측 도구가 이 환경에서 전부 hang**: `lsof -p`, `psutil.Process().cwd()`, `curl localhost:3000`, `urllib` 모두 무응답(파이프/find/grep 계열 sandbox hang과 동일 계통).
- 확정된 사실: 원본 리포 `frontend/.next/BUILD_ID = Dwq0DX9YlhYac8GqeiLro`(2026-05-24), worktree엔 `.next` 없음.
- **논리 결론**: ⑳-2 카드 리스트(a6a32db)·지도(aa972b5)는 전부 07-21 커밋이고 메모리상 ⑳-2는 배포·라이브 확인됨. 05-24 빌드에 07-21 코드가 있을 수 없으므로, **:3000 서빙 트리는 원본 리포가 아닌 별도 web 런타임 트리**(⑳-F Q4가 측정한 05-24 .next는 서빙 트리가 아님 = 부분 오측정)일 가능성이 높다. 단 실측 미완이므로 **S3는 빌드 상태와 무관하게 안전한 표시층 처치(오버레이) + 배포 시 재빌드 절차** 양쪽을 채택.
- **후속 처방**: 서빙 cwd 판별은 향후 `next-server` 부모 스크립트/런타임 트리 문서(reference_daphne_api_tree_sync_gap)로 확인하거나, 배포 재빌드 후 HTTP BUILD_ID로 실측.

### 0-3 basis_summary 실물 (1줄 노출 적합성)

| 유형 | 길이(min/max/avg) | 형태 | 노출 |
|---|---|---|---|
| SUPPLIES_TO/COMPETES_WITH/DEPENDS_ON/PARTNER_WITH | 52~110 | "SEC 10-K: …" (이미 캡됨) | 말줄임 1줄 |
| PEER_OF | 7~15 | "Peer 관계 + 같은 산업" | 그대로 |
| CO_MENTIONED | 10 | "뉴스 동시출현 N회" | 그대로 |
| PRICE_CORRELATED | 10 | "주가 상관 0.60" | 그대로 |

전 유형 basis 존재(PEER 레거시 2건만 빈값). **HALT(비정형 대용량) 미해당** → 진행. 서버측 캡 `BASIS_SUMMARY_MAX_LEN=160` 방어 추가.

### 0-4 등급 대응표 (ground truth — S1 라벨 매핑 근거)

점수 계단값은 `evidence_tier_best`(1/2/3) 및 relation_status와 대응. 표시점수 = truth 관계는 `truth_score`, market 관계는 `market_score`.

| relation_type | cat | 표시점수 계단값(지배) | 소스 |
|---|---|---|---|
| COMPETES_WITH | truth | 85(96%) | sec_filing |
| SUPPLIES_TO/DEPENDS_ON/PARTNER_WITH | truth | 85(67~87%) | sec_filing |
| PEER_OF | truth | 60(73%)·85·35 | market_peer |
| CO_MENTIONED | market | 35(count<5)·60·85 | co_mention |
| PRICE_CORRELATED | market | 35(corr<0.6)·60·85 | price_corr |

→ **등급 매핑 확정**: 표시점수 85→confirmed, 60→likely, 35→observed, 그 외/0→unverified. 소스는 relation_type 그룹.

### 0-5 baseline

- pytest chainsight: **303 passed, 1 error**(그 error는 `psycopg2 DeadlockDetected` — 동시 실행한 Django shell과 DB 락 경합, 코드 무관 환경 이슈). ego API 19개 통과.
- vitest chainsight: 재구성 후 **205 passed / 23 files**, tsc `--noEmit` **0 error**.

---

## S1 — 백엔드: ego API 등급·근거 additive

`apps/chain_sight/api/ego_views.py` (기존 필드 전부 불변):

- edges[]에 추가: `grade`(계단값→등급 코드, `_grade_by_score`), `grade_source`(relation_type→소스, `GRADE_SOURCE_BY_TYPE`), `basis_summary`(서버 캡 160자), `last_observed_at`(신규 명시 필드, last_mentioned와 동일값).
- **표시점수는 카테고리 분기**: truth 관계=truth_score, market 관계=market_score (market 관계가 truth_score=0이라 등급 unverified로 뭉개지는 것 방지).
- 동일 `values()` 컬럼 추가만 — **N+1 없음**(쿼리 수 상수급 테스트 통과).
- contract 먼저: `contracts/shared-types.ts` EgoEdge additive + `EgoGrade`/`EgoGradeSource` 타입.
- 테스트 `tests/chainsight/test_ego_api.py::TestEgoGradeFields` 8종 신규 → **27 passed**.

## S2 — 프론트: 카드 리스트 재구성

`RelationCardList.tsx` 재구성 + `cardListConfig.ts` 상수 분리:

- **연속 신뢰도 바 폐지** → 등급 배지("확정 · 공시" / "유력 · 동종" / "관찰 · 뉴스", 등급+소스 병기). `GRADE_LABELS`/`GRADE_COLORS`/`GRADE_SOURCE_LABELS` 상수.
- **유형별 섹션 분리**: 공급망 / 경쟁 / Peer / 시장 신호 / (기타). `SECTION_ORDER` 상수(순서 고정), 섹션 헤더에 개수·소스 설명 1줄.
- **basis_summary 1줄 노출**(truncate + hover 전체). 뉴스만 "뉴스 근거 N건", **공시(SEC)는 건수 미표기**(⑳-F evidence 0건 오해 차단).
- **날짜 "확인일"** + last_observed_at 사용.
- **tie-break 정렬**(`sortInSection`): 등급 내림차순 → 뉴스 근거수 → 심볼 알파벳(⑳-F Q3 동점 순서 미정의 해소).
- 절단 총량·더보기·GraphStatePanel 유지. 테스트: `cardListConfig.test.ts`(등급·섹션·정렬) + `RelationCardList.test.tsx`(섹션·배지·근거·확인일) 재작성.

## S3 — 지도 뭉침 조건부 처치 (오버레이 + 재빌드 병행)

STEP 0-2 판별 미완 → 안전한 양쪽 채택:

- **오버레이(표시층 처치, 추가 force 튜닝 없음)**: `MarketGraphCanvas.tsx`에 `simStabilized` state. 방사형(centerSymbol) 모드에서 시뮬레이션 안정화(onEngineStop→fx/fy 주입→zoomToFit) 완료 전까지 "관계 배치 정리 중..." 오버레이로 초기 뭉침 프레임을 가림(`pointer-events-none`, 상호작용 비차단). 중심/섹터 전환마다 리셋.
- **재빌드 절차**: 배포 단계에서 FE `npm run build && npm run start`로 aa972b5(zoomToFit 정합) 서빙 반영 확인. 규칙 A에 "FE 변경 시 빌드+재시작" 단계 반영(공통 하네스).

## S4 — 이벤트 보드 위계 (표시층, 데이터 무변경)

`EventBoard.tsx` className만:

- 등락률 = 최상위 강조(`text-lg`→`text-2xl font-extrabold`).
- 티커 주표기 강화(`text-sm font-semibold`→`text-base font-bold`), 키워드 부제 대비 유지(gray-400).
- 관심도·종목수 보조 강등(`text-xs gray-500/600`→`text-[11px] gray-400`).
- 테스트 3종 추가(위계 클래스 검증). 기존 EventBoard 테스트 전량 통과(텍스트 불변).

---

## 검증 (additive 증빙)

| 항목 | 결과 |
|---|---|
| pytest ego API | 27 passed (기존 19 + 신규 8) |
| vitest chainsight | 205 passed / 23 files |
| tsc --noEmit | 0 error |
| 마이그레이션 | 0 (스키마 무변경) |
| 기존 API 필드 | 불변(회귀 가드 테스트 통과) |

## S5 — 라이브 렌더 검증

배포(FE 재빌드) 후 캡처 4종: ① NVDA 카드 섹션·등급 배지·basis·확인일 ② SEC 관계 "근거 0건" 오해 소멸 ③ 지도 초기 뭉침 비노출 ④ 이벤트 보드 위계. **배포·재빌드 후 수행 예정**(사용자 로그인 필요).

## S6 — 원장

- DECISIONS: `D-GRADE-HONEST-UI`(연속 바 폐지·등급 라벨화, RC 정규화는 "유형 통합 랭킹 필요 시 선행"으로 재정의) + STEP 0-2 빌드 판별(오버레이+재빌드 병행).
- TASKQUEUE: evidence 카운터 SEC 집계 백로그 / RC 정규화 재정의.
- common-bugs: "표시 필드 명명은 근원 필드 의미 실측 후"(last_mentioned=auto_now 오라벨) + 서빙 cwd 판별 도구 hang(부분 오측정 리스크).
