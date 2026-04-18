# Chain Sight 작업 지시서 v1.4 — 전수 검증 보고서

> **검증일**: 2026-04-17
> **대상**: 업로드된 20개 작업 지시서
> **기준 문서**: ROADMAP v1.3, CHAIN_SIGHT_PM v1.2, 이전 대화 확정 결정사항

---

## 1. 파일 현황

### 업로드된 파일 (20개)

| Phase | 파일 | 작업 번호 | 상태 |
|-------|------|----------|------|
| 0 | cs_00, cs_01, cs_02, cs_03 | CS-0-0 ~ CS-0-3 | ✅ 정상 |
| 1 | cs_11, cs_12, cs_13 | CS-1-1 ~ CS-1-3 | ✅ 정상 |
| 2 | cs_21, cs_22, cs_23, cs_24, cs_25 | CS-2-1 ~ CS-2-5 | ⚠️ cs_25 수 불일치 |
| 3 | cs_31, cs_32, cs_33 | CS-3-1 ~ CS-3-3 | ✅ 정상 |
| 4 | cs_41, cs_42, cs_43, cs_44, cs_4_10 | CS-4-1~3, CS-4-4, CS-4-10 | ⚠️ 흐름 끊김 + 파일명 |

### 누락된 파일 (이전 대화에서 생성했으나 미업로드)

| 예상 번호 | 내용 | 이전 대화 출처 |
|----------|------|-------------|
| cs_45 | Watchlist CRUD API | "로드맵 v1.4 연쇄 변경사항 정리" 세션 |
| cs_46 | Summary Path 생성 | 동일 세션 |
| cs_47 | Simple Actions API (archive/resolve) | 동일 세션 |
| cs_48 | Recheck API | 동일 세션 |
| cs_49 | Expand API | 동일 세션 |
| cs_51~cs_58 | Phase 5 프론트엔드 (8개) | "로드맵 이후 다음 단계" + "v1.4 연쇄" 세션 |
| cs_61~cs_65 | Phase 6 백엔드 (미확정) | CHANGES_v1.4에서 언급 |
| cs_71~cs_73 | Phase 7 프론트엔드 (미확정) | CHANGES_v1.4에서 언급 |

---

## 2. 발견된 이슈

### 🔴 High — 수정 필수 (3건)

**H1. cs_25: Celery Beat 스케줄 수 불일치**

목표 란에 "9개 스케줄 등록"이라고 쓰고, 완료 기준에는 "8개 스케줄 등록"으로 적혀 있다. 실제 코드 블록에는 9개가 나열되어 있다.

- 코드 내 9개: co-mention-daily, heat-score-daily, profiles-weekly, price-comovement-weekly, relation-confidence-weekly, stale-decay-weekly, chain-profile-weekly, sync-profiles-weekly, sync-relations-weekly
- 완료 기준의 "8개"는 오류

수정안: 완료 기준을 "Celery Beat **9개** 스케줄 등록"으로 변경.

---

**H2. cs_44: "다음 작업" 연결 끊김**

현재: `→ 다음: CS-5-1 (GraphView.tsx) 또는 CS-5-5 (MarketView.tsx)`

문제: cs_44(Seed Node) 뒤에 cs_45~cs_4_10(Watchlist API 6개)이 와야 한다. 현재 연결대로면 Watchlist API를 건너뛰고 바로 프론트엔드로 넘어간다.

수정안: `→ 다음: cs_45 (Watchlist CRUD API)`

---

**H3. cs_43: "다음 작업" cs_44 건너뜀**

현재: `→ 다음: cs_45 (Watchlist API 시작)`

문제: cs_43(Trace API) → cs_44(Seed Node) → cs_45(Watchlist CRUD)가 맞는 순서인데, cs_44를 건너뜀.

수정안: `→ 다음: cs_44 (Seed Node heat_score)`

---

### 🟡 Medium — 수정 권장 (4건)

**M1. cs_4_10: 파일명 규칙 불일치**

다른 파일: `cs_XX_이름.md` (cs_41, cs_42, cs_43, cs_44)
이 파일: `cs_4_10_alternatives_api.md`

일관성을 위해 `cs_410_alternatives_api.md`로 변경하거나, 현재 네이밍 유지 시 "두 자리를 넘는 번호는 언더스코어로 구분"이라는 규칙을 명시해야 한다.

---

**M2. cs_4_10: 선행 조건 "CS-4-9 완료" — 해당 파일 미존재**

cs_4_10의 선행 조건이 CS-4-9(Expand API)인데, cs_49 파일이 업로드되지 않았다. 이 파일이 로컬에 존재하는지 확인 필요.

---

**M3. cs_4_10: M4 마일스톤 조건 충족 불가**

완료 기준에 `★ M4 달성: "API 완성 + Path Watchlist 백엔드 완성"`이 있는데, Watchlist 관련 API(cs_45~cs_49)가 없으면 M4를 달성할 수 없다. cs_4_10만으로는 "Path Watchlist 백엔드 완성"이 아니다.

---

**M4. cs_44: 로드맵 버전 표기 누락**

다른 19개 파일은 모두 `> **로드맵 버전**: v1.4` 형식으로 표기하는데, cs_44만 이 줄이 없다.

---

### 🟢 Low — 참고 (3건)

**L1. cs_22: ChainNewsEvent 중간 저장 명시 — 이전 이슈 해결됨 ✅**

이전 리뷰에서 "ChainNewsEvent 사용처 없음"이 중요 이슈였는데, 현재 cs_22에서 ChainNewsEvent를 중간 저장소로 활용하도록 명시되어 있다.

---

**L2. cs_32: basis_summary Neo4j 저장 — 정상 ✅**

CHANGES_v1.4 M1에서 "Expand 후보에 basis_summary 포함" 요구가 있었고, cs_32의 sync 코드에서 `basis_summary: rel.relation_basis_summary`를 Neo4j 엣지에 저장하고 있다.

---

**L3. cs_41: CUSTOMER_OF 역방향 파생 — 이전 이슈 해결됨 ✅**

로드맵 v1.3의 핵심 변경사항 "SUPPLIES_TO만 canonical, API에서 역방향 파생"이 cs_41에 `reverse_label = 'CUSTOMER_OF'` 로직으로 구현되어 있다.

---

## 3. 이전 리뷰(9개 이슈) 반영 상태

| # | 이슈 | 상태 | 근거 |
|---|------|------|------|
| 1 | Neo4j 인덱스 초과 추가 (cs_03) | ✅ 해결 | 로드맵 정의 2개만 유지, "추가하지 않는다" 명시 |
| 2 | GraphRepository 시그니처 변경 (cs_02) | ⚠️ 미해결 | 로드맵은 upsert_node(label, properties), cs_02도 동일. 실구현 시 bulk_upsert 등 추가될 수 있으나 현재는 정합 |
| 3 | ChainNewsEvent 사용처 없음 | ✅ 해결 | cs_22에서 중간 저장소로 명시 |
| 4 | Celery Beat 미배정 | ✅ 해결 | cs_25에서 전체 등록 (다만 수 불일치 H1) |
| 5 | CUSTOMER_OF 역방향 미구현 | ✅ 해결 | cs_41에서 reverse_label 로직 포함 |
| 6 | Tier B EventReaction 미작성 | ⚠️ 유지 | cs_21에서 "별도 작업 지시서로 분리, 현재 미작성" 명시. 의도적 보류. |
| 7 | Neo4j 동기화 Celery Beat 미포함 | ✅ 해결 | cs_25에서 sync-profiles/sync-relations 등록 |
| 8 | M4 explanation+market_signals | ✅ 해결 | cs_41에서 explanation=basis_summary, market_signals={co_mention, price_corr} 매핑 |
| 9 | DC 트랙 지시서 없음 | ⚠️ 유지 | 의도적 보류 (M1.5 진입 시 작성) |

---

## 4. 결정 필요 사항

### 결정 1: 누락 파일 처리

이전 세션에서 cs_45~49, cs_51~58 파일을 생성했으나 Claude 세션 리셋으로 소실. 로컬에 남아있는지 여부에 따라 조치가 달라진다.

**선택지 A**: 로컬에 파일이 있다 → 이 대화에 업로드하면 검증 진행

- 장점: 이전 작업 재활용, 시간 절약
- 단점: 이전 세션 파일이 최신 변경(CHANGES_v1.4의 10개 수정)을 반영했는지 재확인 필요
- 유지보수: 업로드 후 교차검증 1회 추가

**선택지 B**: 로컬에 파일이 없다 → 새로 생성

- 장점: 최신 로드맵 v1.4 + PM v1.2 + CHANGES_v1.4를 한 번에 반영하여 깨끗한 상태
- 단점: 작업 시간 필요 (cs_45~49 5개 + cs_51~58 8개 = 13개 파일)
- 유지보수: 생성 후 검증 1회

**선택지 C**: Phase 4 백엔드(cs_45~49)만 먼저 생성, 프론트(cs_51~58)는 Phase 4 완료 후

- 장점: 원칙 4 부합 ("나중에 필요할 수도 있는" 지시서를 미리 안 만듦), Phase 0부터 실행 시작 가능
- 단점: 프론트 작업 진입 시 다시 생성 작업 필요
- 유지보수: 2회에 나눠서 생성

**추천: 선택지 A (파일 있으면) 또는 C (없으면)**. Phase 0 착수가 최우선이므로, 당장 필요하지 않은 Phase 5 프론트 지시서까지 한 번에 만들 필요 없음.

---

### 결정 2: cs_4_10 파일명

**선택지 A**: `cs_410_alternatives_api.md`로 변경 (일관성 유지)

- 장점: cs_41~cs_49와 동일 패턴
- 단점: 기존 참조 수정 필요

**선택지 B**: 현재 `cs_4_10` 유지

- 장점: 변경 작업 없음
- 단점: 두 자리 숫자 번호 시 혼동 (cs_4_1 vs cs_41)

**추천: A**. 현재 참조가 다른 파일의 "→ 다음" 링크뿐이므로 수정 비용 최소.

---

### 결정 3: Phase 6/7 (cs_61~73) 위치 확정

이전 대화에서 "Phase 6 신설하여 Watchlist를 독립 Phase로"를 선택했는데, 업로드된 파일에는 Phase 6/7 파일이 없고 cs_45~cs_4_10이 Phase 4 안에 포함되어 있다.

**선택지 A**: Phase 4에 통합 유지 (CS-4-5 ~ CS-4-10 = Watchlist APIs)

- 장점: Phase 수 증가 없음, 현재 파일 구조와 일치
- 단점: Phase 4가 10개 작업으로 비대 (기존 3개 → 10개)
- 1인 개발 관점: Phase 4가 길어지지만 "API 전체"가 한 Phase라 맥락 전환 없음

**선택지 B**: Phase 6/7 독립 분리 (이전 대화 결정 유지)

- 장점: 각 Phase가 3~5개로 균형, "그래프 탐색 API"와 "Watchlist API"의 역할 구분 명확
- 단점: Phase 번호 재배정 필요, 마일스톤도 재조정
- 1인 개발 관점: Phase가 많아지면 진행 상황 파악이 오히려 쉬울 수 있음

**추천: A (Phase 4 통합)**. 이유:
1. 업로드된 파일 구조가 이미 Phase 4 통합 형태 (cs_45, cs_4_10이 모두 Phase 4)
2. Phase 6/7 분리는 프론트엔드(Phase 5)까지 포함한 더 큰 재조정이 필요
3. 현재 Phase 0조차 착수 전이므로 Phase 4 구조는 나중에 실행 직전에 재검토해도 됨

---

## 5. 즉시 수정 가능한 항목

H1~H3 + M4는 현재 업로드된 파일에서 바로 수정 가능하다. 수정하겠는가?

| # | 파일 | 수정 내용 |
|---|------|----------|
| H1 | cs_25 | 완료 기준 "8개" → "9개" |
| H2 | cs_44 | → 다음: cs_45 |
| H3 | cs_43 | → 다음: cs_44 |
| M4 | cs_44 | 로드맵 버전 헤더 추가 |

---

## 6. 전체 요약

**좋은 점:**
- Phase 0~3 (cs_00~cs_33, 12개 파일): 내부 일관성 완벽. 선행 조건 체인, 마일스톤 매핑, 완료 기준 모두 정합.
- 이전 9개 이슈 중 6개 완전 해결, 2개 의도적 보류(EventReaction, DC 트랙) 상태 명시됨.
- cs_41의 CUSTOMER_OF 역방향, explanation/market_signals, is_watched prefetch가 로드맵 v1.3 변경사항을 충실히 반영.
- cs_44(Seed Node)가 가장 상세한 파일로, 계산 로직/헬퍼 함수/가중치 튜닝 계획/엣지 케이스까지 커버.

**수정 필요:**
- 즉시 수정: H1(cs_25 수 오타), H2/H3(다음 작업 링크), M4(버전 표기)
- 결정 후 수정: 파일명(M1), 누락 파일 처리(결정 1), Phase 구조(결정 3)

**현재 실행 가능 여부:**
- Phase 0~3: **즉시 실행 가능** (cs_00~cs_33, 12개 파일 완비)
- Phase 4 그래프 API: **실행 가능** (cs_41~cs_43, 3개 파일 완비)
- Phase 4 Seed Node: **실행 가능** (cs_44 완비, 다만 "다음 작업" 링크만 수정)
- Phase 4 Watchlist API: **파일 확인 필요** (cs_45~cs_49 미업로드)
- Phase 5 프론트엔드: **파일 확인 필요** (cs_51~cs_58 미업로드)

---

**END OF DOCUMENT**
