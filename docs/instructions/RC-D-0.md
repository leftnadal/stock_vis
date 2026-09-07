# 지시서 RC-D-0 — 관계 store 이중화 전수 실측 + RC-PAIR-DEDUP 프로브 (read-only · 상신 후 HALT)

> **세션 종류:** ops/chainsight 측정 전용. 코드 변경 0 · PG 쓰기 0 · Neo4j 쓰기 0.
> **기대 base:** origin/main `087c7cd8` 이후 (2026-09-04 14:17 KST). 그 이전이면 fetch 후 재확인, 그래도 다르면 HALT.
> **worktree:** origin/main 기준 신규 브랜치 `monorepo/sess-rc-d0` (트리 `sv-rc-d0`).
> **목적:** D 결정(RelationConfidence = 관계 단일 정본) 집행 설계에 필요한 사실을 독립 전수 측정. 처분·통합·제약 신설 구현은 이 세션 범위 밖.
> **캐리오버 금지:** "기대값"은 과거 스냅샷. 전부 이번 세션에서 다시 잰다. 다르면 실측 채택 + 차이 명시.

## 근거 앵커
- TASKQUEUE.md:1532 CS-STORE-DEDUP — RelationConfidence 13,701 vs serverless StockRelationship 225,073(HELD_BY_SAME_FUND 197k·SAME_REGULATION 26k).
- TASKQUEUE.md:1596 RC-PAIR-DEDUP — status∈CP·max>0 입력 2,365행 무향 collapse 시 2,199 엣지 −166(왕복 33 + 동방향 중복 111쌍, {2:126,3:15,4:2,5:1}).
- DECISIONS.md:7009~ RC-A-1 3결정 · DECISIONS.md:7140 D-RC-C1-STORAGE.

## §0 STEP 0
- 0-1. git fetch → origin/main 해시. 087c7cd8 이후 아니면 HALT.
- 0-2. worktree sv-rc-d0 / 브랜치 monorepo/sess-rc-d0 생성. 해시 보고.
- 0-3. [0번 게이트] 이 지시서를 docs/instructions/RC-D-0.md로 커밋.
- 0-4. pytest tests/architecture GREEN + health_check ❌ 신규 0.

## STEP 1 — 코드 전수 조사 (grep, 실명 인용)
- 1-1. 두 store 모델 좌표·스키마 ⑴ serverless 관계 store(파일:라인·클래스·전 필드·choices) ⑵ RelationConfidence(파일:라인·식별 필드·Meta 원문) ⑶ 양측 유일성 제약 현황 그대로.
- 1-2. serverless 관계 store 직접 소비처 전수 grep(파일별 건수, 테스트·마이그 별도). apps/ 참조 건수 명시.
- 1-3. write 경로 전수(create/bulk_create/update_or_create/get_or_create/update/delete 파일:라인 + 파이프라인).
- 1-4. HTTP 서빙 경로(view·URL) + frontend 실호출 여부(생성타입 vs 실호출 구분).
- 1-5. 승격 경로(serverless→RelationConfidence) 존재 여부 + 두 모델 동시 참조 파일 목록.
- 1-6. Neo4j 동기화 경로 2개 비교(파일:라인·Cypher 원문·노드 라벨·키·DB 설정 키·동일 그래프 판정).

## STEP 2 — 창고 실측 (PG, SELECT만)
- 2-1. serverless 관계 store 총행 + relationship_type별 내림차순 전건. 최다 1종 제외 잔여 + 상위 2종 제외 잔여 둘 다.
- 2-2. source_provider × relationship_type 교차표 상위 15.
- 2-3. discovered_at 최신 5 + 월별 분포(유입 중 vs 동결).
- 2-4. RelationConfidence 총행 + relation_status·relation_type·score_version 분포.
- 2-5. 교집합(타입 집합 교집합 + LEAST/GREATEST 방향정규화 양측 공존 심볼 쌍 수).

## STEP 3 — RC-PAIR-DEDUP 프로브
- 3-1. RC 무향 pair 2행+ 전수: pair 수·행수 분포·relation_type 조합 상위 20. 3분류(ⓐ같은방향 ⓑ왕복 ⓒ혼합) pair 수·행수.
- 3-2. ⓐ 발생 writer 특정(1-3 대조) + 표본 3건 first_observed_at·evidence_sources.
- 3-3. (a,b,relation_type) 제약이 ⓐ 막는지 판정. 못 막으면 111쌍 재정의 + 실효 제약 후보(구현 금지).
- 3-4. 델타 재현: status∈CP ∧ market_score>0 → collapse 엣지. 2,365→2,199(−166) 산식.
- 3-5. pair_aggregation.py 합산 vs 최대 코드 인용 + 표본 3건 evidence_count_total·truth_score 대조.
- 3-6. 판정 1줄: 중복이 근거수·점수 부풀리는가 Y/N.

## STEP 4 — Neo4j 위생 (Cypher 읽기전용)
- 4-1. :Stock 총수 + 각 키 프로퍼티 보유 노드 수 + 둘다 보유(이중노드).
- 4-2. MATCH ()-[r]->() type별 count. PRICE_CORRELATED=0 재확인.
- 4-3. serverless 유래 엣지 타입·건수(backbone 잡음 여부).
- 4-4. django_celery_beat serverless 동기화 활성 스케줄(enabled) 유무.

## STEP 5 — 상신 + HALT
- 5-1. docs/reports/rc_d0_store_dedup_recon.md 작성·커밋. 코드 변경 0.
- 5-2. TASKQUEUE CS-STORE-DEDUP·RC-PAIR-DEDUP 정정 + RC-D-0 측정완료 표기. PROGRESS.
- 5-3. 처분·통합·삭제·제약 신설 안 함. 후보만 + HALT.
- 5-4. push는 "푸시" 대기.

## 금지·경계
- read-only 엄수(PG SELECT·Neo4j MATCH/RETURN). --apply/makemigrations/migrate 금지.
- 파괴적 작업·원격 브랜치 삭제·.git/hooks·launchd = 디렉터 유보(INC-006: 안전확인≠집행권한).
- 자기 브랜치·worktree 삭제 금지(INC-006 재발방지). packages/shared 무수정·apps→shared 단방향.

## HALT 조건
base 불일치 / Neo4j 접속 불가 / 3-4 산식 −166 불일치 / STEP 1 전제 모델·경로 부재·의미 상이 / 예상 밖 일체.
