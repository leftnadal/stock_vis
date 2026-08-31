# RC-C-1: SymbolCentrality + backbone 뷰 슬라이스 1

> 세션 지시서 (병진 발행 · 2026-08-31). worktree `sv-rc-c1` / branch `monorepo/sess-rc-c1` (origin/main 기준).
> push = "푸시" 지시 대기(D-PUSH-DELEG). prod DB 파괴적 작업·원격 브랜치 삭제 금지.

## §0 프리플라이트 (수치 캐리오버 금지 — 전 항목 재측정)
- 0-1. git fetch → origin/main HEAD 보고. e0450aa1(after-snapshot 보고서)이 origin/main에 landing됐는지 확인 — 미landing이면 보고만(병진 몫, HALT 아님).
- 0-2. [0번 게이트] 이 지시서를 docs/instructions/RC-C-1.md로 커밋 후 착수.
- 0-3. RC 실측: 총행(기대 13,626+유입) · [0,1] 밖 값 0 · version 3.0 전행 · PC 0행 유지 · PEER 2행(outlier) 존재 확인.
- 0-4. 그래프 재료 실측: status∈{confirmed, probable} 엣지 수(활성 해자) · max(truth,market) ≥ 0.85 엣지 수 · 심볼 노드 수(distinct symbol_a∪b). → PageRank 대상 그래프의 실규모 확정.
- 0-5. 의존성: networkx 설치 여부(설치돼 있으면 사용, 없으면 순수 파이썬 power-iteration 구현 — 신규 패키지 설치는 보고 후 지시 대기).
- 0-6. 기존 centrality 코드 확인: apps/chain_sight의 centrality 관련 선존 모듈(RC-SURVEY-0에서 소비자로 언급됨) — 신설과 중복인지, 확장인지 판정 재료 보고. 중복이면 확장 우선(복제 금지).

## STEP 1 — 계산 (BE)
- 1-1. 모델 SymbolCentrality(apps/chain_sight, 앱-로컬 유지): symbol(unique) · pagerank(float) · degree(int) · computed_at · score_version · 계산 파라미터 기록 필드(damping, edge_filter 요지). 신규 테이블 additive — 마이그레이션 파일 생성까지, migrate 적용은 병진 몫(공유 DB 규약).
- 1-2. compute_symbol_centrality 태스크: 입력 = RC에서 status∈{confirmed,probable} AND max(truth,market)>0 엣지(PEER outlier 2행 제외 명시). 가중 무향 그래프 → PageRank(damping 0.85 표준). 전 노드 upsert + 이전 실행 대비 상위 20 순위 변동 로그.
- 1-3. 경계: RC 정본만 읽기 — serverless StockRelationship 접근 금지(D-RC-STORE 결정). DB 읽기는 chain_sight 앱 내부이므로 합법(app-로컬).
- 1-4. beat 등록은 하지 않는다 — PeriodicTask 초안(주 1회, 일요 06:00 ET)을 상신 문서로만 작성(beat DB 변경 = 병진 승인 규약). 세션 내 1회 수동 실행(foreground)으로 실데이터 채움.
- 1-5. 테스트: 소형 고정 그래프의 PageRank 기지값 일치 · outlier 제외 · 빈 그래프 no-op · upsert 멱등.

## STEP 2 — API
- 2-1. GET /api/v1/chainsight/backbone/ (IsAuthenticated): 응답 {as_of, top_symbols: [{symbol, pagerank, degree}](limit 파라미터, 기본 20), edges: [{symbol_a, symbol_b, score(=max), category, evidence_count, observed_count, trust}] — 상위 심볼 유도 부분그래프의 θ≥0.85 엣지만. θ는 하드코딩 금지: score_scale.py 단일 소스에서 import.
- 2-2. 캐시 15분(선례 동형). 테스트: 인증 필수 · 빈 상태 shape · θ 경계.

## STEP 3 — FE (승인 목업 = 시각 계약)
- 3-1. /chainsight/backbone 라우트(AuthGuard). 좌: 중심성 top-N 리스트(막대) · 우: 그래프(θ≥0.85 실선, 그 외 상위 심볼 간 엣지 점선) · 하단: 엣지 선택 시 근거 바(점수·category·근거 수·재관측 횟수·신뢰 뱃지). 그래프 렌더는 기존 market-graph 구현 자산 재사용 가능 여부 §0-6 판정 따름.
- 3-2. /chainsight 메인에 진입 링크 1건(기존 NAV_ITEMS 무변).
- 3-3. data-guide="chainsight.backbone" 루트 앵커만(콘텐츠는 GUIDE 트랙 등재).
- 3-4. vitest: 렌더 · 빈 데이터 · 엣지 선택 바 · θ 필터. tsc 0 · lint 순증 0.

## STEP 4 — 검증·하네스
- 4-1. pytest 전체+architecture GREEN · 행위보존: 기존 파일 diff = 진입 링크 1건+urls 등록에 한정(목록 입증).
- 4-2. 수동 1회 실행 실측 보고: 노드·엣지 수, top 20 심볼과 pagerank 값, 계산 소요 시간 — 목업 가상치를 실값으로 대체할 재료.
- 4-3. 라이브(:3100 가능 시) 스크린샷 2장(백본 뷰·엣지 선택 상태). 불가 시 2회 내 중단·잔여 등재.
- 4-4. DECISIONS(D-RC-C1: 목업 승인 08-31·계승 파라미터) · TASKQUEUE(C-1 완료, beat 상신 대기, GUIDE 앵커 이관, D구현 트랙 후속) · PROGRESS.

## 보고
§0 실측 → 파일 목록 → 테스트 표 → 4-2 실값 → 스크린샷/잔여 → 하네스 요지 → HALT(푸시·migrate·beat는 병진 지시 대기).

## HALT 조건
architecture RED / 기존 파일 diff 초과 / §0-6 중복 판정 곤란 / 예상 밖 일체.
