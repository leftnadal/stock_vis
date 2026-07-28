# 설계 — OPS-WORKTREE-ISOLATION v1 (동시성 사고 근본 대책)

- 문서 상태: FINAL 설계안 + 결정 회부문. **구현 착수는 회부 후 사용자 결정으로.**
- 성격: 설계·회부 문서(코드 무접촉). 대상 = 세션·자동화·공유 트리 간 동시성 사고의 구조적 대책.
- 계보: 동시성 사고 3건(07-04·07-06 ×2) + T-3b 트랙에서 실전 검증된 격리 패턴 4건.
- 관련: `DECISIONS.md`(소프트강제 ADR·SESSION_CONTRACT), `docs/harness/SESSION_CONTRACT.md`, `docs/harness/EXTERNAL_AUTOMATION_DEFENSE_GUIDE.md`, `reference_worker_runtime_tree`/`reference_daphne_api_tree_sync_gap`(메모리).

---

## §1. 입력 — 사고와 실증의 대차대조

### 사고 3건 (원인 계열이 각기 다름)

| # | 시점 | 사고 | 원인 계열 |
|---|---|---|---|
| 1차 | 07-04 13:13 | **작업트리 탈취** — 외부 세션/rehome 자동화가 공유 작업트리를 `checkout origin/main`(detached)으로 점유, celery-worker도 origin/main 코드로 재시작(pair 모델·태스크 부재 → 다음 틱 unregistered 위험) | rehome 계열 자동화가 **세션 작업 중 트리 점유** |
| 2차 | 07-06 | **nightly 리셋 vs 워커** — `worker_sync.sh`가 `sv-worker-runtime`을 origin/main으로 고정 → 기본 워커가 pair 전용 aggregate 태스크 미보유, 매 틱 unregistered, period 미적립(영구 갭), verify FAIL | 자동화가 **워커 런타임 트리를 main으로 고정**(구조 충돌) |
| 3차 | 07-06 | **공유 트리 미커밋 WIP** — TH-1(theme heat) 세션의 untracked/미커밋 파일이 in-place merge를 차단 → 격리 worktree merge로 우회해야 함 | 공유 트리 **미커밋 WIP가 통합을 차단** |

### 검증된 패턴 4건 (T-3b 등 실전 실증 — 설계의 기초 자재)

| 패턴 | 실증 | 효과 |
|---|---|---|
| **일회용 격리 worktree**(생성→작업→제거) | T-3b `sv-t3b`·`sv-t3b-merge`·`sv-t3b-docs` 등 다회, theme-heat `sv-theme-heat` | 세션 작업이 공유 트리·타 세션과 완전 격리. 상주 금지와 양립 |
| **원격 전용 refspec push**(`branch:main`, 무체크아웃 통합) | D2 T-1 pair→main, T-3b `push origin HEAD:main` | 공유 트리 무접촉 통합. in-place merge의 WIP 겹침 회피 |
| **세션 이탈 시 WIP 커밋 의무**(전용 브랜치로) | 3차 사고의 직접 교훈, feedback `commit_pathspec_shared_main` | 미커밋 WIP가 통합·타 세션을 막는 것 방지 |
| **sv sync 표준 경로 + 재기동 전후 PID·코드버전 실측** | T-3b 배포(`sv sync` → PID 80710/80714 + inspect + HEAD 실측), #47 자기가드 | 워커 런타임 트리를 자동화 단독 소유로. stale 사본 실행 차단 |

---

## §2. 요구사항 (설계가 충족해야 할 것)

- **R1 워커 런타임 트리 단독 소유**: `sv-worker-runtime`(및 web/api 런타임 트리)은 **자동화 단독 소유** — 세션 직접 조작 금지, 갱신은 `sv sync` 경로만. (2차 사고 대책)
- **R2 세션 작업 = 일회용 격리 worktree**: 표준 수명주기(생성·명명 규약 `monorepo/sess-*`·작업·**제거**)로. 상주 worktree 금지 유지. (1차 사고 대책)
- **R3 공유 트리 역할 재정의**: `~/Desktop/stock_vis`의 세션 점유 규칙·이탈 시 WIP 커밋 의무·`.env` 등 untracked 런타임 설정의 소유권 명시(T-4 판정 전례 = untracked 설정은 git/코드/WIP 범위 밖). (3차 사고 대책)
- **R4 통합 = 원격 전용 refspec 기본**: push는 `branch:main` / `HEAD:main` 무체크아웃 경로를 기본으로. (3차 사고 회피 실증)
- **R5 위반의 탐지 가능성**: 사고가 **조용히 어긋나지 않고 시끄럽게 실패하거나 기록**될 것. (전 계열 공통 — silent drift 방지)

---

## §3. 설계 선택지 (사용자 결정용)

### Opt-1 — 규약 + 헬퍼 (경량)
- **구성**: 문서 규약 + 헬퍼 스크립트 `wt-open`/`wt-close`(격리 worktree 생성·정리 자동화, 명명 규약 강제, 이탈 시 WIP 커밋 프롬프트).
- **강제력**: 없음 — 규율 준수에 의존(R5 미충족).
- **구현**: 반나절.

### Opt-2 — 규약 + 가드 (중량, 예상 추천선)
- **구성**: Opt-1 + 강제 장치 —
  - 공유 트리 git hook: 보호 브랜치 체크아웃 경고·dirty 상태 이탈 경고(3차).
  - nightly/rehome이 **세션 마커 파일 존중**(마커 존재 시 리셋 skip + 로그) — 1·2차 근본 차단.
  - 워커 런타임 트리 수동 조작 탐지(#47 자기가드 확장).
- **강제력**: 사고 3건 전 계열 커버 + R5(시끄러운 실패/기록) 충족.
- **구현**: 1~2일.

### Opt-3 — 전면 재구조 (중장기, 등재만)
- **구성**: 트랙별 고정 worktree 풀 + 중앙 조정 데몬.
- **강제력**: 최대 커버리지.
- **비용**: 1인 운영에 과잉 — 상시 유지비·복잡도. **등재만**(현 단계 채택 비권장).

### 정량 비교표 (초안)

| 기준 | Opt-1 경량 | Opt-2 가드 | Opt-3 재구조 |
|---|---|---|---|
| 사고 1차(트리 탈취) 커버 | △ 규율 의존 | ✅ 마커 존중 | ✅ |
| 사고 2차(워커 리셋) 커버 | △ | ✅ 런타임 단독소유+탐지 | ✅ |
| 사고 3차(미커밋 WIP) 커버 | ○ 프롬프트 | ✅ hook 경고 | ✅ |
| 구현 비용 | 반나절 | 1~2일 | 주 단위 |
| 운영 마찰(1인) | 낮음 | 중 | **높음(상시)** |
| 강제력(R5) | ✗ | ✅ | ✅ |
| 재발 면역 | 약 | 강 | 강 |

---

## §4. 결정 회부문

- **회부 안건**: OPS-WORKTREE-ISOLATION 구현 범위 = Opt-1 / **Opt-2(예상 추천)** / Opt-3(등재).
- **추천 근거**: 사고 3건이 서로 다른 계열(트리 탈취·워커 리셋·미커밋 WIP)이라 **규율 의존(Opt-1)만으로는 재발**(1·2차는 자동화가 세션 규율 밖에서 작동 — 세션만 구속하는 임시 규칙이 2차를 못 막은 것이 실증). R5(시끄러운 실패)는 강제 장치(Opt-2) 필요. Opt-3은 1인 운영 과잉.
- **선결 조건**: T-3b §4 관찰 종결 + 정리 목록 순서(DB beat 삭제 → pair 브랜치 삭제) 이후 착수(트리거 = pair→main 통합 완료, 이미 충족). §6 동결과 무겹침 시점에 사용자 호출.
- **미결 세부(구현 시 확정)**: 세션 마커 파일 포맷·위치(SESSION_CONTRACT §C 헤더 연동), nightly가 존중할 마커 프로토콜, git hook의 경고 vs 차단 수위(소프트강제 ADR 계보).

**구현 착수는 본 회부에 대한 사용자 결정 후.** 결정 시 SESSION_CONTRACT/EXTERNAL_AUTOMATION_DEFENSE_GUIDE와의 정합(중복 규약 단일 출처 = repo 하네스) 확인.
