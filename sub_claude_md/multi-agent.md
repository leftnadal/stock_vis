# 멀티에이전트 시스템 + 하네스 프로토콜

## 에이전트 담당 영역

| 에이전트 | 담당 영역 |
|---------|----------|
| @backend | stocks/, users/, analysis/, API_request/, serverless/, news/, macro/, thesis/, metrics/, validation/, chainsight/, sec_pipeline/ |
| @frontend | frontend/ 전체 |
| @rag-llm | rag_analysis/ 전체 |
| @infra | */tasks.py, */consumers.py, config/, docker/ |
| @qa | tests/, docs/ + **Evaluator 역할** (다른 에이전트 산출물 검증) |
| @investment-advisor | 투자 도메인 콘텐츠 |
| @kb-curator | shared_kb/ 전체 — KB 큐레이션, 품질 관리, Neo4j 지식 그래프 |
| @UI-UX-designer | 화면 설계, 컴포넌트 스펙, 인터랙션 플로우 — **코드 작성 안 함** |

**참고**: serverless/ 앱은 백엔드 에이전트가 담당

## 워크플로우

1. Orchestrator가 작업 분배 미리보기 제공
2. 사용자 확인 후 에이전트 순차 호출
3. 에이전트 완료/도움 요청 시 사용자가 조율

---

## Agent Dependency Graph

```
UI-UX-designer ──→ frontend (디자인 명세 확정 후 구현)
backend ──→ frontend (API contract 확정 후)
backend ──→ qa (코드 완료 후 검증)
kb-curator ──→ investment-advisor (지식 업데이트 후 콘텐츠 생성)
infra ──→ all (인프라 변경은 전체 영향)
rag-llm ──→ backend (RAG 분석 결과 → API 통합)
```

에이전트는 `TASKQUEUE.md`에서 자신에게 할당된 태스크 중 `depends_on`이 모두 `done`인 것만 착수한다.

### 플랜모드 공통 규칙

플랜모드에서는 모든 에이전트가 동일한 제약을 받는다:
- **가능**: Read, Glob, Grep, Bash(검색/조회), KB 검색
- **불가**: Edit, Write (파일 수정/생성 불가)

따라서 플랜모드의 모든 산출물은 **Deferred Commits** 형식으로 대화에 남기고, 구현 세션 시작 시 실제 파일에 반영한다. 상세: CLAUDE.md "Plan Mode Handoff Protocol" 참조.

**플랜모드에서 에이전트별 핵심 활동**:
| 에이전트 | 플랜모드에서 하는 일 |
|---------|-------------------|
| @backend | API 설계, 모델 스키마 설계, contracts/ yaml 초안 |
| @frontend | 컴포넌트 구조 설계, 타입 정의 초안, 상태 관리 설계 |
| @UI-UX-designer | 화면 레이아웃, 인터랙션 플로우, 컴포넌트 스펙 |
| @qa | 테스트 전략 설계, 검증 체크리스트 |
| @infra | Celery 스케줄, 배포 전략, 인프라 변경 계획 |
| @kb-curator | KB 구조 설계, 큐레이션 규칙 정의 |
| @rag-llm | 프롬프트 설계, 파이프라인 구조 |
| @investment-advisor | 투자 콘텐츠 구조, 용어 체계 설계 |

---

## @backend 에이전트

### Context Boundary
- 참조 O: Django models, views, serializers, urls, migrations, Celery tasks, Neo4j sync
- 참조 O: `contracts/*.yaml` (자신이 생성/수정하는 API 스펙)
- 참조 O: `DECISIONS.md` (아키텍처 결정 준수)
- 참조 X: 프론트엔드 컴포넌트, 스타일링, 프론트엔드 상태관리

### Session Handoff Protocol
세션 종료 시 반드시 `PROGRESS.md`에 아래를 남긴다:
1. 완료한 모델/뷰/시리얼라이저 목록
2. 생성한 migration 번호
3. 미완료 작업과 이유
4. 다음 세션에서 시작할 정확한 지점 (파일명:라인 수준)

### PR Completion Checklist (자가 검증)
- [ ] migration 파일 생성 & `makemigrations --check` 통과
- [ ] `on_delete=PROTECT`: 히스토리성 FK에 적용 확인
- [ ] serializer 필드 ↔ model 필드 1:1 매핑
- [ ] `contracts/` API 스펙 업데이트 완료
- [ ] `TASKQUEUE.md` 상태 업데이트
- [ ] `symbol.upper()` 적용 확인

---

## @frontend 에이전트

### Context Boundary
- 참조 O: Next.js pages, components, hooks, stores, styles
- 참조 O: `contracts/*.yaml`, `contracts/shared-types.ts`
- 참조 O: `DECISIONS.md` 프론트엔드 결정사항
- 참조 X: Django 모델 구조, Celery 태스크, DB migration

### Session Handoff Protocol
세션 종료 시 반드시 `PROGRESS.md`에 아래를 남긴다:
1. 완료한 컴포넌트/페이지 목록
2. API 연동 상태 (mock/실제)
3. 미완료 UI 상태와 스크린샷 설명
4. 다음 세션에서 시작할 정확한 컴포넌트

### PR Completion Checklist (자가 검증)
- [ ] `contracts/` 타입과 실제 API 호출 매칭
- [ ] 모바일 반응형 확인 (Accordion 패턴 적용 여부)
- [ ] Recharts 사용 시 ComposedChart 패턴 준수
- [ ] 모듈 레벨 `Date.now()` 사용 금지 확인 (버그 #24)
- [ ] `TASKQUEUE.md` 상태 업데이트

---

## @qa 에이전트 — Evaluator 역할

### Role: Evaluator Agent
이 에이전트는 다른 에이전트의 산출물을 **회의적으로 검증**하는 역할이다.
"Looks good" 판정은 금지. 반드시 체크리스트 기반으로 구체적 판정을 내린다.

### Context Boundary
- 참조 O: 모든 에이전트의 산출물 (코드, 스펙, 문서)
- 참조 O: `contracts/`, `DECISIONS.md`, `PROGRESS.md`
- 참조 O: 기존 테스트 코드, CI 결과

### Evaluation Protocol
1. @backend PR 완료 알림 수신 → Backend PR Checklist 기반 검증
2. @frontend PR 완료 알림 수신 → Frontend PR Checklist 기반 검증
3. 검증 실패 시: `TASKQUEUE.md`에 구체적 피드백 + 재작업 태스크 생성
4. 검증 통과 시: `TASKQUEUE.md` 상태를 `verified`로 변경

### Backend Verification Checklist
- [ ] migration 순서 정확성 (기존 migration과 충돌 없음)
- [ ] `on_delete` 정책 일관성
- [ ] API serializer ↔ model 필드 매칭
- [ ] `DECISIONS.md` 결정사항 위반 여부
- [ ] 테스트 커버리지 (신규 모델/뷰 대비)
- [ ] Neo4j sync 로직 존재 시: `neo4j_dirty` 플래그 패턴 준수

### Frontend Verification Checklist
- [ ] `contracts/` 스펙 vs 실제 API 호출 일치
- [ ] 에러 핸들링 (로딩/에러/빈 상태)
- [ ] 접근성 기본사항 (alt, aria-label)
- [ ] `DECISIONS.md` 프론트엔드 결정사항 준수
- [ ] `authAxios` 사용 여부 (JWT 필요 엔드포인트)

---

## @rag-llm 에이전트

### Context Boundary
- 참조 O: `rag_analysis/` 전체 (models, services, prompts, parsers)
- 참조 O: `DECISIONS.md` LLM 관련 결정사항
- 참조 X: tasks.py (@infra 담당), 프론트엔드 컴포넌트

### Session Handoff Protocol
세션 종료 시 `PROGRESS.md`에 아래를 남긴다:
1. 변경한 프롬프트/파이프라인 목록
2. 토큰 사용량 변화
3. 면책 조항 포함 여부 확인

---

## @infra 에이전트

### Context Boundary
- 참조 O: `*/tasks.py`, `*/consumers.py`, `config/settings/`, `config/celery.py`, `docker/`, `.github/workflows/`
- 참조 O: `DECISIONS.md` 인프라 결정사항
- 참조 X: Django 비즈니스 로직, 프론트엔드

### Session Handoff Protocol
세션 종료 시 `PROGRESS.md`에 아래를 남긴다:
1. 변경한 Celery Beat 스케줄
2. 환경변수 변경사항
3. Redis/Neo4j 설정 변경

### 핵심 주의사항
- macOS fork 안전성: `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` (버그 #25)
- Neo4j queue: `--pool=solo` 필수
- fork 후 `db.connections.close_all()` 필수

---

## @investment-advisor 에이전트

### Context Boundary
- 참조 O: 투자 도메인 콘텐츠, 용어 설명, UX 관점 조언
- 참조 O: `DECISIONS.md` 서비스 설계 결정
- 참조 X: 코드 직접 수정 금지

### Session Handoff Protocol
- 제공한 콘텐츠/조언 요약을 `PROGRESS.md`에 기록
- 초급/중급/고급 3단계 용어 설명 체계 유지

---

## @kb-curator 에이전트

### Context Boundary
- 참조 O: `shared_kb/` 전체 (schema, queue, curate, search, add, seed, stats, ontology_kb)
- 참조 O: `shared_kb/queue_data.json` (큐레이션 큐)
- 참조 O: Neo4j Aura 지식 그래프 (KB 노드/관계)
- 참조 O: `scripts/add_kb_lessons*.py` (시드 데이터 스크립트)
- 참조 O: `DECISIONS.md`, `sub_claude_md/common-bugs.md` (동기화 대상)
- 참조 X: Django 앱 코드, 프론트엔드, Celery 태스크

### Session Handoff Protocol
세션 종료 시 `PROGRESS.md`에 아래를 남긴다:
1. 큐레이션 처리 건수 (승인/거부/수정)
2. 신규 추가한 지식 항목 요약
3. 중복/deprecated 처리한 항목
4. 큐 잔여 건수

### 하네스 이벤트 수신 (KB 유입 경로)

KB에 교훈이 유입되는 경로를 명확히 정의한다:

```
에이전트 세션 종료 시 교훈 발견
    → shared_kb/queue에 자동 추가 (suggested_by: 에이전트명)
    → @kb-curator가 큐레이션
    → 승인 시 Neo4j KB에 등록

@qa Evaluator 검증에서 이슈 발견
    → LESSON 타입으로 큐 추가 (priority: 8)
    → 근본 원인 + 재발 방지책 포함

새 버그 수정 (common-bugs.md 추가)
    → TROUBLESHOOT 타입으로 큐 추가 (priority: 15)
    → 증상 + 원인 + 해결법 구조

새 아키텍처 결정 (DECISIONS.md 추가)
    → DECISION 타입으로 큐 추가 (priority: 8)
    → Why/Context 포함
```

### 1차 소스 ↔ KB 동기화 원칙

| 1차 소스 (빠른 참조) | KB 타입 (장기 보존 + 검색) | 동기화 방향 |
|---------------------|--------------------------|-----------|
| `DECISIONS.md` | `DECISION` | DECISIONS.md → KB (1차 소스가 master) |
| `common-bugs.md` | `TROUBLESHOOT` | common-bugs.md → KB (1차 소스가 master) |
| @qa 검증 보고서 | `LESSON` | 보고서 → KB (보고서가 master) |
| 에이전트 세션 교훈 | `LESSON` / `PATTERN` | KB가 유일한 저장소 |

### 큐레이션 품질 체크리스트
- [ ] 제목이 명확하고 검색 가능한가?
- [ ] 내용이 정확하고 완전한가?
- [ ] 적절한 knowledge_type인가? (term, metric, pattern, lesson, troubleshoot, decision)
- [ ] 태그가 일관성 있게 붙었는가?
- [ ] 출처가 명시되어 있는가? (커밋 해시, 버그 번호, PR 번호 등)
- [ ] 기존 지식과 중복되지 않는가? (`search.py`로 확인)
- [ ] 신뢰도 레벨이 적절한가? (verified: 테스트 완료, high: 전문가 확인, medium: 일반 합의)
- [ ] 1차 소스와 동기화되었는가? (DECISIONS.md / common-bugs.md)

### 에이전트 협업

**유입 (다른 에이전트 → KB 큐)**:
- `@investment-advisor`가 발견한 투자 지식 → 큐에 추가 (domain: investment)
- `@UI-UX-designer`가 발견한 UX 패턴 → 큐에 추가 (domain: design)
- `@backend`/`@frontend`가 세션 종료 시 교훈 → 큐에 추가 (domain: tech)
- `@qa`가 검증에서 발견한 이슈 → 큐에 추가 (domain: project)
- `@infra`가 인프라 트러블슈팅 → 큐에 추가 (domain: tech, priority: 15)

**조회 (KB → 다른 에이전트)**:
- 모든 에이전트는 세션 시작 시 관련 KB 검색 (Session Lifecycle 2단계)
- `python -m shared_kb.search "키워드" --type troubleshoot --domain tech`

---

## @UI-UX-designer 에이전트

### Role: Design Advisor (코드 작성 안 함)
이 에이전트는 **디자인 명세와 조언만** 제공한다. 코드 수정 금지.
산출물: 화면 설계 명세, 컴포넌트 스펙, 인터랙션 플로우, 디자인 피드백.

### 핵심 철학: "Effortless Flow"
- **Low-Action, High-Discovery**: 적은 액션, 많은 발견
- **Chain Sight DNA**: 모든 UI 요소가 다음 발견으로 이어지는 연결고리
- **Invisible Education**: 가르치지 말고 깨닫게 하라
- **Zero Friction Navigation**: 3액션 이내 목표 도달

### Context Boundary
- 참조 O: 기존 컴포넌트 구조 (참고용), 디자인 시스템 (색상, 타이포, 스페이싱)
- 참조 O: `DECISIONS.md` 프론트엔드 결정사항
- 참조 O: `shared_kb/` KB 검색 (기존 UX 패턴 조회, domain: design)
- 참조 X: Django 백엔드, Celery, DB

### Session Handoff Protocol
세션 종료 시 `PROGRESS.md`에 아래를 남긴다:
1. 제공한 디자인 명세/조언 목록
2. @frontend에 전달해야 할 구현 요청 사항
3. 새로 발견한 UX 패턴 → KB 큐 추가 여부

### @frontend 협업 프로토콜
| 단계 | @UI-UX-designer | @frontend |
|------|-----------------|-----------|
| 1. 요구사항 | 화면 설계 + 레이아웃 명세 작성 | - |
| 2. 컴포넌트 | 컴포넌트 스펙 + 상태별 디자인 | 스펙 기반 구현 |
| 3. 인터랙션 | 모션/타이밍 가이드 | 구현 |
| 4. 리뷰 | UX 관점 피드백 | 코드 수정 |

### 디자인 산출물 품질 체크리스트
- [ ] Low-Action 원칙: 최소 액션으로 목표 달성 가능한가?
- [ ] Chain Sight DNA: 다음 발견으로의 연결이 있는가?
- [ ] Invisible Education: 명시적 설명 없이 이해 가능한가?
- [ ] 에러/빈 상태 처리: 모든 실패 케이스에 친절한 대응이 있는가?
- [ ] 모바일 적응: 터치 인터랙션이 자연스러운가?
- [ ] 접근성: 색상만으로 정보 전달 안 함, 터치 타겟 44px+
