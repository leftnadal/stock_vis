# 지시서 ⑳-1 실행 보고 — 중심성 리더보드 (UI 트랙 1단계)

**세션**: 실행 · **날짜**: 2026-07-16
**worktree**: `monorepo/sess-20-leaderboard` (base origin/main `01486cc`) · **머지 금지(push까지)**
**HALT 미발동** · Neo4j 기동 0 · 외부 API 0 · prod DB 쓰기 0(로컬 read-only 실측만)

---

## STEP 0 — ground truth 실측

| 항목 | 실측 |
|---|---|
| origin/main HEAD | `01486cc` (⑲ `f3302de` 포함 ✓) |
| **centrality/top/ 실제 응답** | `{as_of, metric, n, graph_size:{nodes,edges}, results:[…]}` — H1 스키마 가정 일치 |
| results 항목 필드(⑲ 기존) | `symbol, pagerank, betweenness, pagerank_rank, betweenness_rank, graph_nodes, graph_edges` |
| **지표 필드 목록** | **pagerank · betweenness** (2종). degree/closeness 없음 |
| SymbolCentrality 모델 | symbol(CharField)·as_of·pagerank·betweenness·pagerank_rank·betweenness_rank·graph_nodes·graph_edges. unique=(symbol, as_of) |
| 로컬 DB 데이터 | **1일치(2026-07-16, 555행)** → rank_delta 현재 null 경로 |
| ego rank 노출 | ego 노드에 `pagerank_rank`·`betweenness_rank`(⑲ S3, additive null) — 리더보드 rank와 일관 |
| pytest baseline | **3892 passed · 53 skipped · 0 failed** |
| chainsight vitest baseline | 152 passed(신규 전) |

**⚠ 스키마 갭 발견·해소(H1 유관)**: 실측 API `results`에 **name 부재**. 지시서 S2 컬럼 "종목(심볼+이름)"이 name을 전제 → 하드 HALT 대신 **name을 additive로 추가**(S1 동일 파일 centrality_views.py, Stock join). additive·저위험이라 라운드트립 없이 진행, 본 보고서에 명시.

---

## S1 — 백엔드: rank / rank_delta / name additive 확장

`centrality/top/` results 각 항목에 **additive** 추가(기존 7필드·top-level 키·컨슈머 무변경):
- `rank`: 요청 지표 기준 당일 순위(= `{metric}_rank`)
- `rank_delta`: 전일_rank − 당일_rank(상승=양수). **전일 = 당일보다 앞선 가장 최근 as_of**(주말·휴일 갭 허용). 전일 부재 시 **null**. 2쿼리(prev_as_of + prev ranks)로 N+1 방지
- `name`: 종목명(Stock join, 미등재 심볼 "") — S2 컬럼용

**마이그레이션 무발생**(스키마 무변경, `makemigrations --check` = No changes → H4 아님).
**테스트 7신규**: delta 상승/하락/불변 · null · 갭(전전일 사용) · 지표별 rank(betweenness) · additive 필드 보존 · name join · N+1 방어. **centrality 21 passed**.

## S2 — 프론트: 중심성 리더보드 화면

- **라우트** `/chainsight/leaderboard` (`app/chainsight/leaderboard/page.tsx` → `CentralityLeaderboard` 컨테이너)
- **테이블**(`CentralityLeaderboardTable`, presentational): 순위 / 종목(심볼+이름, ego 링크) / 중심성값 / 전일대비 / 관계망 링크
- **rank_delta 3상태**: ▲상승(rose·한국축 강세) · ▼하락(sky·약세) · —(0/null 중립). 색 = `colorSemantics.CHANGE_TEXT` 재사용, **신규 색 0**
- **ego 진입 URL**: `/chainsight/market-graph?focus=SYMBOL` (PG 네이티브 ego 화면. `/chainsight/[symbol]` Deep Dive는 D-A2-DEEPDIVE 폐기라 미사용). ※ market-graph focus는 seed 심볼만 초점(비-seed는 기본 뷰) = **기존 제약**(변경 금지 범위)
- **지표 드롭다운**: pagerank / betweenness
- **설정 상수 분리**(`leaderboardConfig.ts`): `LEADERBOARD_LIMIT`(20) · `LEADERBOARD_METRICS`(라벨+포맷) · `LEADERBOARD_COLUMNS` · `egoUrlForSymbol` — 코드 수정 없이 튜닝
- 타입 `CentralityTopResponse`/`Item` = `contracts/shared-types.ts` SSoT + `types/chainsight.ts` 재export. `fetchCentralityTop` 서비스 + `useCentralityTop` 훅(TanStack Query)
- UI 용어 "테마" 금지 준수 — "중심성 리더보드/관계망/허브·매개" 사용

**vitest 8신규**(렌더·delta 3상태·null·ego URL·지표 포맷·빈 케이스). **chainsight scoped 160 green**(회귀 0), **tsc 0**.

## S3 — 원장 정산

- **DECISIONS 2**: D-CENTRALITY-UI-TRACK(A 리더보드→C 백본, A 4.50 vs C 4.20 마진 0.30·A⊂C 무손실) · D-DISCOVERY-WATCH(관찰 대기 A 4.40 vs B 2.70 마진 1.70).
- **TASKQUEUE 2**: Q20-DISCOVERY-REMEASURE(07-30경 재측정, 전제 ⑦) · Q20-2-BACKBONE-GRAPH(착수=⑳-1 배포+ego 메모).
- **common-bugs 2**: celery 태스크 신설 등록 누락 DoD(⑲ 실증) · pre-commit iCloud 경고 무해.
- PROGRESS 갱신 · 본 보고서.

---

## 회귀 (DoD 게이트)

- pytest: baseline 3892 유지 + S1 신규 7 green, 신규 red 0 (전체 회귀 = 커밋 후 실행, 수치 커밋 메시지/PROGRESS 기재)
- vitest: chainsight scoped 160 green(신규 8 포함) · tsc 0. ※full-suite react-query flake는 선존 환경(node v22.19.0 격리 필요, scoped OK — [[project_color_ops_testenv_arc]])
- additive 증빙: `test_additive_existing_fields_preserved`(기존 7필드+top-level 키 불변)
- 설정 상수 분리: `leaderboardConfig.ts`
- 신규 celery 태스크 **0**(이번 지시서엔 없어야 정상 — 확인)
- 마이그레이션 **무발생**(H4 아님)

## 병진 수동 대기 (순서)

1. `monorepo/sess-20-leaderboard` 브랜치 머지 (원장 4파일 merge=union 자동 병합)
2. **sync + daphne·(web) 재시작** — FE는 web 런타임 트리(next dev) + daphne(API). **migrate 불필요**(스키마 무변경)
3. **화면 실물 확인** — `/chainsight/leaderboard` 라이브 렌더(리더보드 테이블·rank_delta 색·ego 링크 이동). [[feedback_ui_slice_live_screenshot]] 규약상 실화면 캡처 전까지 "완료" 미확정 (배포=병진이므로 이 세션 범위 밖)
