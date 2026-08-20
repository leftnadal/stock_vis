# EVT-SURVEY-2 — 관계 데이터·모델 선례·캡 실측 (read-only)

목적: EVT-CHAIN(관계 이벤트 뷰) 타당성과 D-EVT-1b(원장 배치 위치) 결정 재료 수집.
구현·모델 생성·기존 파일 수정 금지.

## §0 프리플라이트
0-1. worktree ~/worktrees/sv-evt-0 재사용. `git fetch origin` → HEAD·origin/main 해시 보고.
0-2. [0번 게이트] 본 지시서를 docs/instructions/EVT-SURVEY-2.md로 저장, 해당 1파일만 명시 add 커밋. push 금지.
0-3. 이후 read-only. foreground 실행, 기계 시계만(#89). 외부 콜은 §3의 최대 3콜만 인가.

## STEP 1 — RelationConfidence 실측 (read-only SQL)
1-1. 모델 좌표(파일:라인)와 스키마 필드 전수 인용 — 특히 관계 유형(type) 필드 존재 여부.
1-2. 총 엣지 수 / distinct 종목 수 / confidence 분포(min·p25·p50·p75·max).
1-3. 유니버스 교차: 현행 유니버스 구성종목 중 confidence 상위 엣지(p50 이상 기준) 1개 이상 보유 비율.
1-4. 시나리오 프로브: AI 인프라 대표 시드 1종목(예: NVDA)의 1-hop 이웃 수와 confidence 상위 10 목록.
1-5. 저장 위치 판정: 이 데이터만으로 관계 이벤트 조인이 Postgres 단독 가능한지,
     Neo4j 필요 요소(경로 탐색 등)가 있는지 사실 기준으로 기술.

## STEP 2 — 배치 위치·흡수 판단 재료
2-1. packages/shared 내 Django Model 서브클래스 전수(0건인지 실측 — "캘린더성"이 아니라 전체).
2-2. macro/models EconomicEvent 스키마 필드 원문 인용.
2-3. chain_sight Filing(FORM_IPO)·get_stock_splits 소비부 필드 요약 (B′ 통합 원장 설계 대조용).
2-4. TASKQUEUE:1361 SPLIT-CALENDAR-PREVIEW 원문 전문 인용 (흡수 범위 확정용).

## STEP 3 — FMP 응답 캡 실측 (최대 3콜, 예산 확인 후)
3-1. earnings-calendar 90일 창 1콜 → 반환 건수(캡 도달 여부 판단).
3-2. dividends-calendar 90일 창 1콜 → 동일.
3-3. (캡 징후 시에만) 창 절반으로 1콜 재시도 → 캡 경계 추정.

## 보고 형식
- STEP별 표. 1-2·1-3은 SQL과 결과 병기. 쓰기 = §0-2 커밋 1건 입증(git status).

## HALT 조건 (HALT-0 기본)
- 예상 밖 조건 일체 → 즉시 HALT + 보고
