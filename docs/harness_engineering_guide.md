# 하네스 엔지니어링 가이드 — Stock-Vis

> "Agent = Model + Harness"
> 모델 외부의 모든 인프라(컨텍스트 관리, 상태 영속화, 오케스트레이션, 검증 루프)를 체계적으로 관리한다.

---

## 1. 핵심 개념

### 하네스(Harness)란?
LLM 에이전트가 효과적으로 작동하기 위해 필요한 **모델 외부의 모든 인프라**:
- **컨텍스트 관리**: 무엇을 읽고, 무엇을 버릴 것인가
- **상태 영속화**: 세션 간 지식/진행 상태 유지
- **오케스트레이션**: 에이전트 간 작업 흐름 조율
- **검증 루프**: 산출물의 품질을 체계적으로 검증

### 왜 하네스 엔지니어링인가?
- 프롬프트만으로는 멀티세션/멀티에이전트에서 **일관성** 유지 불가
- 에이전트가 "이전 세션에서 뭘 했는지" 모르면 **중복 작업** 발생
- API 변경 시 프론트엔드가 몰라서 **인터페이스 불일치** 발생
- "Looks good" 리뷰는 **버그를 통과**시킴

---

## 2. Stock-Vis 하네스 아키텍처

```
CLAUDE.md (루트)
├── Harness Protocol (Session Lifecycle, Context Rules, Contract-Driven Dev)
├── sub_claude_md/ (기능별 상세 → 에이전트가 작업 시 참조)
│   └── multi-agent.md (에이전트별 Context Boundary + Handoff + Checklist)
│
├── PROGRESS.md      ← 세션 간 상태 영속화
├── DECISIONS.md     ← 아키텍처 결정 단일 소스
├── TASKQUEUE.md     ← 에이전트 간 오케스트레이션
└── contracts/       ← API 인터페이스 계약
    ├── chainsight-api.yaml
    ├── validation-api.yaml
    ├── sec-pipeline-api.yaml
    └── shared-types.ts
```

---

## 3. Session Lifecycle

### 3.1 세션 시작
```
1. PROGRESS.md 읽기 → 현재 상태 파악
2. DECISIONS.md 읽기 → 아키텍처 제약 인지
3. TASKQUEUE.md 읽기 → 내 태스크 확인 (depends_on 모두 done?)
4. 관련 sub_claude_md/*.md 읽기 → 도메인 컨텍스트 확보
```

### 3.2 작업 중
- **Context Management**: 50줄 초과 출력은 파일로 오프로드
- **Compaction**: 이전 PR 결과는 1줄 요약으로 압축
- **Contract-First**: API 변경 시 contracts/ 먼저 업데이트

### 3.3 세션 종료
```
1. PROGRESS.md 업데이트 (상태, blocker, 다음 할 일)
2. TASKQUEUE.md 태스크 상태 변경
3. contracts/ 변경사항 반영
```

---

## 4. Contract-Driven Development

### 원칙
> **스펙이 진실의 소스**. 스펙과 구현이 불일치하면 구현을 수정한다.

### 흐름
```
@backend: contracts/chainsight-api.yaml 업데이트
    ↓
@frontend: shared-types.ts 동기화 + API 호출 코드 생성
    ↓
@qa: 스펙 vs 실제 응답 비교 검증
```

### 파일 구조
| 파일 | 역할 | 소유 |
|------|------|------|
| `*.yaml` | OpenAPI 3.0.3 스펙 | @backend |
| `shared-types.ts` | 프론트엔드 공유 타입 | @frontend (yaml 기반) |

---

## 5. Evaluator Pattern

### @qa의 Evaluator 역할
- "Looks good" 판정 **금지**
- 체크리스트 기반 구체적 판정만 허용
- 검증 실패 → TASKQUEUE.md에 재작업 태스크 생성
- 검증 통과 → TASKQUEUE.md 상태 `verified`로 변경

### 검증 흐름
```
@backend PR 완료
    ↓ (알림)
@qa: Backend Checklist 검증
    ├── 통과 → TASKQUEUE status: verified
    └── 실패 → TASKQUEUE에 재작업 태스크 + 구체적 피드백
```

---

## 6. Context Boundary 원칙

각 에이전트는 **자신의 영역만** 참조하고, 다른 에이전트 영역은 `contracts/`를 통해서만 소통한다.

```
@backend  ←→  contracts/*.yaml  ←→  @frontend
    ↕                                    ↕
DECISIONS.md                      DECISIONS.md
    ↕                                    ↕
TASKQUEUE.md  ←→  @qa (검증)  ←→  TASKQUEUE.md
```

### 금지 패턴
- @frontend가 Django models.py를 직접 읽고 타입 추론 → contracts/shared-types.ts 사용
- @backend가 React 컴포넌트 구조를 참고해 API 응답 설계 → contracts/ 스펙 기반
- @infra가 비즈니스 로직 수정 → @backend에 TASKQUEUE 태스크 생성

---

## 7. Error Message as Teaching

### 원칙
실패 메시지는 "무엇이 잘못됐는지"가 아니라 "어떻게 고치는지"를 알려준다.

### 예시

**Bad**:
```
AssertionError in test_peer_selection
```

**Good**:
```
test_peer_selection 실패: PeerGroup.get_peers()가 size_bucket 파라미터를
받지 않음. models.py의 get_peers 시그니처에 size_bucket: str = 'all' 추가 필요.
참고: DECISIONS.md "1차 검증 > Peer 프리셋 6종" 섹션 확인.
```

---

## 8. 하네스 유지보수

### 갱신 주기
| 파일 | 트리거 |
|------|--------|
| `PROGRESS.md` | 매 세션 종료 |
| `DECISIONS.md` | 새로운 아키텍처 결정 발생 시 |
| `TASKQUEUE.md` | 태스크 상태 변경 시 |
| `contracts/*.yaml` | API 엔드포인트 변경 시 |
| `CLAUDE.md` | 새 기능 완료, 버그 추가 시 |
| `sub_claude_md/*.md` | 기능 상세 변경 시 |
| `HARNESS_FITNESS.md` | 월 1회 정기 평가 |

### 하네스 적합도 평가
`HARNESS_FITNESS.md`에서 하네스 시스템의 현재 건강도를 추적한다.
월 1회 정기적으로 평가하고, 문제 발견 시 즉시 개선한다.

---

## 9. 관련 파일 맵

```
프로젝트 루트/
├── CLAUDE.md              # 프로젝트 개요 + 하네스 프로토콜
├── PROGRESS.md            # 세션 간 상태
├── DECISIONS.md           # 아키텍처 결정
├── TASKQUEUE.md           # 태스크 오케스트레이션
├── HARNESS_FITNESS.md     # 하네스 적합도 추적
├── contracts/             # API 계약
│   ├── README.md
│   ├── chainsight-api.yaml
│   ├── validation-api.yaml
│   ├── sec-pipeline-api.yaml
│   └── shared-types.ts
├── sub_claude_md/         # 기능별 상세 (에이전트 참조)
│   ├── README.md
│   ├── multi-agent.md     # 에이전트별 하네스 프로토콜
│   └── *.md               # 기능별 상세
└── docs/
    ├── harness_engineering_guide.md  # 이 파일
    ├── chain_sight/plan/  # 설계서 (DECISIONS.md에서 링크)
    ├── sec_pipeline/plan/ # 설계서 (DECISIONS.md에서 링크)
    └── thesis_control/    # 설계서 (DECISIONS.md에서 링크)
```
