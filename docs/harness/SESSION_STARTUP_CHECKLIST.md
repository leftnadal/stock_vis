# 세션 시작 체크리스트 — 실행 진입점

> **이 문서는 통합 진입점입니다.** 1차 소스는 [`CLAUDE.md` "Session Lifecycle"](../../CLAUDE.md) 입니다.
> 충돌 시 1차 소스가 우선합니다. 본 문서는 **"어떻게 실행하는가"**를, CLAUDE.md는 **"왜/무엇을"**을 다룹니다.

**작성일**: 2026-05-28 (워크플로우 정리 1단계)
**적용 범위**: 모든 Stock-Vis 세션 (Claude / 에이전트 무관)

---

## 매 세션 첫 3단계 (단일 순서)

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
4. KB 큐 추가 — 세션 중 발견한 LESSON/PATTERN/TROUBLESHOOT/DECISION
5. (슬라이스 종결 시) `docs/portfolio/coach/slice{N}/slice{N}_final_report.md` 작성

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
