# 세션 시작 체크리스트 — 실행 진입점

> **이 문서는 통합 진입점입니다.** 1차 소스는 [`CLAUDE.md` "Session Lifecycle"](../../CLAUDE.md) 입니다.
> 충돌 시 1차 소스가 우선합니다. 본 문서는 **"어떻게 실행하는가"**를, CLAUDE.md는 **"왜/무엇을"**을 다룹니다.

**작성일**: 2026-05-28 (워크플로우 정리 1단계)
**적용 범위**: 모든 Stock-Vis 세션 (Claude / 에이전트 무관)

---

## 매 세션 첫 4단계 (단일 순서)

### Step 0 — 세션 계약 헤더 채우기 (먼저)

`docs/harness/SESSION_CONTRACT.md` §C "세션 시작 헤더"의 빈칸(세션 종류 / 소유 앱 / worktree / 브랜치 / 소유 영역)을 채워 **Claude Code에 그대로 붙여 넣는다.** 이 선언이 세션 동안 commit 허용 경로·금지 경로·종료 절차를 결정한다.

- 메인 세션: `apps/<단일 앱>` 하나만 소유 → worktree `../stock_vis_<앱>` · 브랜치 `monorepo/sess-<앱>`
- 관리 세션: 메타 레이어(PROGRESS·DECISIONS·TASKQUEUE·common-bugs·docs·scripts·tests/architecture·health_check) 단독 소유 → worktree `../stock_vis_mgmt` · 브랜치 `monorepo/sess-mgmt`
- 외부 API 세션: `integrations/iron_trading` → worktree `../stock_vis_api` · 브랜치 `iron-trading-api`(기존 재사용)
- 공유 존(`packages/shared`·`config/*`·`packages/web`) 편집 필요 시 **STOP → 사용자 보고 → 단독 확인 후**
- **상속된 인계 메모/타 트랙의 'pending/대기' 주장은 행동 전 그 트랙 현재 장부로 재측정**(추정 전파 금지 — 2026-07 D2 phantom 교훈: 이미 해소된 결정이 구 pending 블록 미갱신으로 stale 잔존).

1차 소스: [`docs/harness/SESSION_CONTRACT.md`](./SESSION_CONTRACT.md) §A 불변 규칙 / §B 소유권 매핑 / §C 헤더 양식 / §E 머지 흐름 / §H 배포 대행(D-DEPLOY-DELEGATE) / §I H1 자가해소(D-H1-SELFRESOLVE)

### Step 1 — 정합성 점검 먼저

```bash
python scripts/health_check.py
```

- **출력**: 7항목 검증표 + exit code (0=OK / 1=warning / 2=error)
- **error 시**: 다른 작업 전 보정 우선 (origin HEAD vs PROGRESS / brunch 부재 / 외부 자동화 무관여 commit 등)
- **warning 시**: 메모만 남기고 진입 가능 — 슬라이스 종결 시 함께 처리
- **모드**: `--quiet` (error/warning만) / `--json` (CI/nightly용, `docs/nightly_auto_system/YYYYMM/DD/health_check.json`로 출력)

1차 소스: [`scripts/health_check.py` 헤더 docstring](../../scripts/health_check.py) / [DECISIONS.md "문서·git 정합성 관리 원칙"](../../DECISIONS.md)

### Step 2 — PROGRESS.md 활성 작업 확인

```bash
sed -n '1,50p' PROGRESS.md
```

- 활성 brunch HEAD / 마지막 갱신일 / 활성 작업 / 다음 할 일 / blocker 확인
- 메모리(`MEMORY.md`)는 캐시일 뿐 — **PROGRESS가 진실의 소스**, PROGRESS가 stale이면 메모리도 stale
- 갱신 우선 순위: **git 현실 → PROGRESS → 메모리**

1차 소스: [CLAUDE.md "Session Lifecycle"](../../CLAUDE.md) / [DECISIONS.md "Claude 메모리는 진실의 소스가 아니라 PROGRESS의 캐시"](../../DECISIONS.md)

### Step 3 — KB 검색으로 사전 교훈 확인

작업 키워드로 직전 교훈/트러블슈팅을 먼저 조회:

```bash
python -m shared_kb.search "<키워드>" --type troubleshoot   # 같은 버그 사례
python -m shared_kb.search "<키워드>" --type lesson         # 반복 실수 패턴
python -m shared_kb.search "<키워드>" --type decision       # 과거 결정 근거
python -m shared_kb.search "<키워드>" --domain tech         # 도메인 필터
```

예:
- Celery 태스크 작업: `python -m shared_kb.search "Celery" --type troubleshoot`
- 외부 자동화 우려: `python -m shared_kb.search "외부 자동화" --type lesson`
- LLM 코스트 관련: `python -m shared_kb.search "CostGuard"`

1차 소스: [CLAUDE.md "KB 컨텍스트 로드"](../../CLAUDE.md) / [`shared_kb/` 검색 모듈](../../shared_kb/)

---

## Step 1~3가 끝나면 — 작업 진입 분기

| 상황 | 다음 행동 |
|------|----------|
| health_check ERROR 잔존 | 보정 commit 먼저 (PROGRESS·DECISIONS·TASKQUEUE 갱신) |
| PROGRESS "다음 할 일" 명시 | 그대로 진입 |
| 사용자가 슬라이스 진입 요청 | 슬라이스 entry 문서 검색(`docs/portfolio/coach/slice{N}/`) 후 진입 |
| 사용자가 자유 요청 | 키워드로 KB 추가 검색 + 관련 문서(`docs/features/`, `sub_claude_md/`) 확인 |
| 플랜모드 진입 지시 | [CLAUDE.md "Plan Mode Handoff Protocol"](../../CLAUDE.md) 의 지연 커밋 패턴 |

---

## 세션 종료 체크리스트 (참고용 — 1차 소스 CLAUDE.md)

세션 종료 시 반드시:

1. `PROGRESS.md` 업데이트 — 현재 상태 / blocker / 다음 할 일
2. 변경된 `contracts/` 파일 동기화
3. `TASKQUEUE.md` 완료 태스크 상태 변경
4. **KB 쓰기 고리 완성** (마지막 칸까지 — 큐는 종착지가 아니다):
   1. **교훈 추출 → 1차 소스에 "먼저 직접" 기록**: 버그·함정은 [`sub_claude_md/common-bugs.md`](../../sub_claude_md/common-bugs.md), 아키텍처 결정은 [`DECISIONS.md`](../../DECISIONS.md). 큐 경유가 아니다 — 큐는 검색KB용 복사본/백업.
   2. **`shared_kb` 큐 드레인 실행**: 밀린 항목 + 당 세션분을 검색KB로 반영. `python -m shared_kb.curate`(대화형) 또는 `--auto`. 상태 점검: `python -m shared_kb.queue_status`.
   3. **교훈 0건이면 "교훈 없음" 명시** (PROGRESS 종료 메모에 한 줄) — 빈손 종료로 누락을 가장하지 않는다.
5. (슬라이스 종결 시) `docs/portfolio/coach/slice{N}/slice{N}_final_report.md` 작성

> 💡 커밋 시 `pre-commit` hook이 `shared_kb` 큐에 3일 이상 미드레인 항목이 있으면 stderr 경고(차단 아님). 경고가 보이면 위 4-2 드레인을 실행.

상세: [CLAUDE.md "Session Lifecycle" §4](../../CLAUDE.md)

---

## 자주 묻는 패턴

### Q. health_check가 warning 1건만 띄울 때 진입해도 되나?

- **DECISIONS 갱신일 warning (60일+)**: 진입 OK. 결정 변경 시 함께 갱신.
- **slice* brunch 미반영 warning**: 진입 OK (정보성). 머지 시점은 사용자 결정.
- **그 외 warning**: 항목별 판단. 보통 진입 가능하지만 PROGRESS "다음 할 일"에 보정 메모.

### Q. 메모리(`MEMORY.md`)와 PROGRESS가 다르면?

- **PROGRESS가 우선**. 메모리는 사후 캐시.
- 메모리 갱신은 세션 종료 시점에 PROGRESS 결과를 반영.

### Q. 외부 자동화(`com.stockvis.nightly`)와 충돌?

→ [`EXTERNAL_AUTOMATION_DEFENSE_GUIDE.md`](EXTERNAL_AUTOMATION_DEFENSE_GUIDE.md) 참조.

---

## 관련 문서

| 문서 | 역할 |
|------|------|
| [CLAUDE.md](../../CLAUDE.md) | **1차 소스** — Session Lifecycle, 하네스 핵심 파일 정의 |
| [DECISIONS.md](../../DECISIONS.md) | 문서·git 정합성 관리 원칙 (2026-05-28) |
| [PROGRESS.md](../../PROGRESS.md) | 현재 활성 상태 |
| [scripts/health_check.py](../../scripts/health_check.py) | 정합성 검증 스크립트 |
| [docs/harness/EXTERNAL_AUTOMATION_DEFENSE_GUIDE.md](EXTERNAL_AUTOMATION_DEFENSE_GUIDE.md) | 외부 자동화 충돌 방어 통합 지도 |
| [docs/portfolio/coach/operational_guide.md](../portfolio/coach/operational_guide.md) | I2 정책 (시간대 회피 + 다층 방어) |
