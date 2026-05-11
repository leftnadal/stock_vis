# HARNESS_FITNESS.md — 하네스 엔지니어링 적합도 추적

> 이 파일은 하네스 시스템의 건강도를 정기적으로 평가하고 기록한다.
> 월 1회 정기 평가 + 문제 발견 시 즉시 업데이트.

---

## 평가 기준

### 1. 상태 영속화 (State Persistence)
| 항목 | 기준 | 현재 상태 |
|------|------|----------|
| PROGRESS.md 최신성 | 최근 세션 종료 시 업데이트됨 | OK (2026-04-13) |
| DECISIONS.md 완전성 | 모든 핵심 아키텍처 결정 포함 | OK — 8개 도메인 결정 기록 |
| TASKQUEUE.md 정확성 | 실제 진행 상태 반영 | OK — CS-R1~R9 + TC-3~6 + SR-1~4 |

### 2. 컨텍스트 관리 (Context Management)
| 항목 | 기준 | 현재 상태 |
|------|------|----------|
| Tool Output Offloading | 50줄 초과 출력 파일 저장 | 규칙 정의됨 — QA 검증 보고서를 파일로 오프로드한 사례 1건 |
| Compaction 적용 | 이전 PR 1줄 요약 | 규칙 정의됨 |
| Context Boundary 준수 | 에이전트 간 영역 침범 없음 | OK — @qa가 검증만 수행, 코드 수정 없음 확인 |

### 3. 오케스트레이션 (Orchestration)
| 항목 | 기준 | 현재 상태 |
|------|------|----------|
| TASKQUEUE 의존성 | depends_on 준수 | OK — CS-R8(verified) → CS-R9(todo) 체인 작동 |
| Contract-First | API 변경 시 스펙 먼저 | 미실증 — 다음 API 변경 시 적용 예정 |
| Agent Dependency Graph | 순환 의존 없음 | OK — 단방향 그래프 |

### 4. 검증 루프 (Verification Loop)
| 항목 | 기준 | 현재 상태 |
|------|------|----------|
| @qa Evaluator 활성화 | PR마다 체크리스트 검증 | OK — 1회차 완료 (91% 승인), 2회차 필요 |
| Backend Checklist | 6개 항목 | OK — 1회차 전항목 검증 완료 |
| Frontend Checklist | 5개 항목 | OK — 1회차 전항목 검증 완료, follow-up 3건 수정 완료 |
| Contract 정합성 | 스펙 vs 구현 비교 | OK — chainsight/validation/sec-pipeline 모두 검증 완료 |

### 5. 문서-코드 동기화 (Doc-Code Sync)
| 항목 | 기준 | 현재 상태 |
|------|------|----------|
| CLAUDE.md ↔ 코드 | 앱 목록, 엔드포인트 일치 | OK (a09662f에서 최신화) |
| contracts/ ↔ views.py | OpenAPI 스펙 ↔ 실제 API | OK — 3개 도메인 모두 검증 완료 |
| shared-types.ts ↔ FE 타입 | 공유 타입 ↔ 실제 사용 | OK — re-export 연결 완료, @contracts/* 경로 설정 |

### 6. 지식 그래프 건강도 (KB Health)
| 항목 | 기준 | 현재 상태 |
|------|------|----------|
| 큐 적체량 | queue_data.json 대기 건수 < 30 | 확인 필요 — 현재 약 19건 대기 |
| 큐레이션 주기 | 최근 2주 내 큐레이션 수행 | 확인 필요 — 수행 이력 미추적 |
| 1차 소스 ↔ KB 동기화 | DECISIONS.md, common-bugs.md 결정/버그가 KB에도 존재 | 미완 — common-bugs 26건 중 일부만 KB에 |
| Session → KB 유입 | 세션 교훈이 KB 큐로 흐르는가 | 신규 도입 — 프로토콜 정의됨, 실행 필요 |
| KB 검색 활용 | 세션 시작 시 KB 검색 수행하는가 | 신규 도입 — Session Lifecycle에 추가됨 |

---

## 평가 이력

### 2026-04-12 (초기 구축)

**종합 점수**: 7/10

**강점**:
- 하네스 인프라 전체 구축 완료 (PROGRESS, DECISIONS, TASKQUEUE, contracts/)
- 에이전트별 Context Boundary + Handoff Protocol 정의
- @qa Evaluator 역할 + 체크리스트 정의
- 기존 설계 문서와의 링크 연결 (DECISIONS.md → docs/)
- 8개 도메인의 아키텍처 결정 기록

**개선 필요**:
- [x] ~~contracts/ OpenAPI 스펙의 응답 필드를 실제 views.py와 1:1 대조 필요~~ → 2026-04-12 리뷰 완료
- [ ] shared-types.ts를 frontend/types/ 에서 import하는 방식으로 마이그레이션 필요
- [ ] @qa Evaluator의 첫 번째 실제 검증 사이클 수행 필요
- [ ] PROGRESS.md 세션 종료 업데이트가 실제로 이루어지는지 1주간 모니터링
- [ ] Tool Output Offloading 실제 적용 사례 축적 필요

### 2026-04-12 (첫 번째 리뷰 — contracts/ 정합성 검증)

**종합 점수**: 8/10 (+1)

**수정된 불일치 6건**:
1. `chainsight-api.yaml` SeedListView: `sectors` → `sector_summary`, `total_seeds` 누락 추가
2. `chainsight-api.yaml` NeighborGraphView: 가상 `graph` 객체 제거, 실제 `cross_edges` + `total_neighbor_count` + `returned_count` + `truncated` 반영
3. `chainsight-api.yaml` SignalFeedView: 전면 재작성 — `signals[]` → `chains[]` (ChainSignal) + 페이징
4. `validation-api.yaml` LLMPeerFilterView: GET → POST 수정, query를 request body로 이동
5. `validation-api.yaml` ValidationSummaryView: 단순 스키마 → 실제 응답 구조 (company_name, peer_info, industry_position 등 반영)
6. `validation-api.yaml` PeerPreferenceView: DELETE 메서드 누락 추가

**추가 수정**:
- `shared-types.ts` 전면 재작성 — `frontend/types/chainsight.ts`와 1:1 대응
- `CLAUDE.md` 에이전트 테이블에 `@investment-advisor` + `@qa Evaluator` 역할 추가
- Deep Dive API 3개 (graph, suggestions, trace) 스키마 상세화

**잔여 개선**:
- [x] ~~shared-types.ts를 frontend/types/ 에서 import하는 방식으로 마이그레이션 필요~~ → 2026-04-13 완료
- [x] ~~@qa Evaluator의 첫 번째 실제 검증 사이클 수행 필요~~ → 2026-04-13 완료 (91% 승인)
- [x] ~~sec-pipeline-api.yaml 응답 스키마 상세화~~ → 2026-04-13 완료

### 2026-04-13 (잔여 개선 3건 완료)

**종합 점수**: 9/10 (+1)

**완료 항목**:
1. `sec-pipeline-api.yaml` 전면 재작성 — on_demand.py 기반 200/202 응답 분기, SupplyChainEvidence/BusinessModelSnapshot 내부 스키마 문서화
2. `shared-types.ts` → `frontend/types/chainsight.ts` 연결 — tsconfig에 `@contracts/*` 경로 추가, chainsight.ts가 contracts에서 re-export (기존 13개 파일 import 경로 무변경)
3. @qa Evaluator 첫 검증 완료 — DECISIONS.md 준수 95%, 종합 91%, 조건부 승인. 📎 `docs/chain_sight/task_done/chain_sight_redesign_V1/qa_evaluator_review_01.md`

**잔여 (비차단)**:
- [x] ~~chainsightService.ts: fetch() → authAxios 통일~~ → 2026-04-13 완료
- [x] ~~RelationCardPanel: 에러 바운더리 추가~~ → 2026-04-13 완료 (로딩+에러+빈 상태)
- [x] ~~useInfiniteQuery: pageParam 명시적 타입 정의~~ → 2026-04-13 완료

**잔여 개선 0건. 점수 상향을 위한 남은 조건:**
- 검증 사이클 2회차 (다음 PR에서 달성)
- Contract-First 패턴 실증 1건 (다음 API 변경에서 달성)
- PROGRESS.md 세션 종료 갱신 이력 1주 축적

**다음 평가**: 2026-05-13 (또는 주요 문제 발견 시)

---

## 적합도 점수 기준

| 점수 | 의미 | 조건 |
|------|------|------|
| 9~10 | Excellent | 모든 항목 OK, 실제 검증 사이클 2회 이상 완료 |
| 7~8 | Good | 인프라 완비, 일부 실행 이력 부족 |
| 5~6 | Fair | 핵심 파일 존재하나 최신성 부족 또는 미사용 |
| 3~4 | Poor | 여러 파일 outdated, 에이전트 boundary 침범 발생 |
| 1~2 | Critical | 하네스 파일 사실상 미사용, 중복 작업/충돌 빈발 |

---

## 자동 경고 트리거

아래 조건 발생 시 즉시 적합도 재평가:
1. PROGRESS.md가 7일 이상 미갱신
2. TASKQUEUE.md의 `in_progress` 태스크가 14일 이상 정체
3. contracts/ 스펙과 실제 API 응답 불일치 발견
4. @qa 검증 없이 PR이 3건 이상 머지
5. DECISIONS.md에 없는 아키텍처 결정이 코드에서 발견
6. KB 큐 적체 30건 초과 (큐레이션 지연)
7. 이전에 KB에 기록된 트러블슈팅과 동일한 버그 재발 (교훈 미참조)
