# 외부 자동화 충돌 방어 — 통합 지도

> **이 문서는 통합 진입점입니다.** 1차 소스는 아래 [관련 1차 소스](#관련-1차-소스) 표의 각 원본입니다.
> 충돌 시 1차 소스가 우선합니다. 본 문서는 **요약 + 포인터**로만 구성되어 있어 복제·중복하지 않습니다.

**작성일**: 2026-05-28 (워크플로우 정리 1단계)
**도입 배경**: Slice 14~17 종결 16일간 167 commit 누적 stale, 외부 자동화 audit commit 끼어들기, #71 사건으로 history 오염

---

## 한 줄 요약

> **자정~새벽 작업 금지** + **매 세션 `health_check.py` 실행** + **Layer 1~4 단계화 진행 중** + **#71 모니터링 잔여**.

---

## 1. 동시 실행 시스템 인지

외부 자동화 두 종류가 작업 디렉토리에서 함께 돌고 있다:

| 시스템 | launchd label | 작업 디렉토리 동작 | 충돌 위험 |
|--------|--------------|------------------|----------|
| 야간 자동화 | `com.stockvis.nightly` | `~/Desktop/stock_vis`에서 자동 git brunch + commit | **edit-time race** |
| Celery 워커 | `com.stockvis.celery-{worker,beat,watchdog}` | read-only | 없음 |

상세 동작 — 1차 소스: [`docs/portfolio/coach/operational_guide.md` §동시 실행 시스템](../portfolio/coach/operational_guide.md)

야간 자동화 스크립트: `~/stock-vis-nightly/run_tier{1,2_be,2_fe,3_audits}.sh`
nightly_v3 스크립트(2026-05-28 신규, Phase 5 health_check 누적): `docs/infra/nightly_v3.sh`

⚠ **사용자 환경 sync 필요**:

```bash
cp ~/Desktop/stock_vis/docs/infra/nightly_v3.sh ~/stock-vis-nightly/nightly_v3.sh
```

cp 안 하면 23:00 nightly의 Phase 5(health_check 누적)가 작동하지 않는다.

---

## 2. 시간대 정책 (I2)

- **권장**: 09:00 ~ 22:00 (KST)
- **금지**: 자정 ~ 새벽 (야간 자동화 활성 시간대)
- **새벽 작업 필요 시**: `launchctl bootout / bootstrap`으로 일시 중지 → 작업 → 재활성화

상세 명령 + 매 작업 시작/직후 체크리스트 — 1차 소스: [`docs/portfolio/coach/operational_guide.md` §I2 정책](../portfolio/coach/operational_guide.md)

---

## 3. 다층 방어 설계

| 계층 | 메커니즘 | 차단 시점 |
|------|----------|----------|
| 시스템-time | 시간대 회피 | 작업 시작 전 |
| edit-time | `git status` 사전 체크 + `WORKSPACE_ROOT.md` 확인 | 편집 직전 |
| commit-time | pre-commit hook 브랜치 화이트리스트 (`#39`) | commit 시도 |
| 추적 | reflog + cherry-pick 패턴 | commit 후 복구 |
| **정합성** | **`scripts/health_check.py`** (2026-05-28 신규, Layer 1) | **매 세션 시작 / 매일 23:00 nightly** |

신규 계층 "정합성"이 추가된 배경 — 1차 소스: [DECISIONS.md "문서·git 정합성 관리 원칙"](../../DECISIONS.md)

---

## 4. 충돌 감지 — 7가지 stale 패턴

`scripts/health_check.py`가 자동 검출하는 7가지:

1. PROGRESS의 `origin/main = <hash>` 표기 vs 실측 (`git rev-parse origin/main`)
2. PROGRESS 언급 brunch / worktree 폴더 존재 여부
3. PROGRESS 마지막 갱신 후 누적 commit 수 (50 초과 warning, 200 초과 error)
4. TASKQUEUE `done` 표기 vs 매칭 git 머지 commit
5. DECISIONS.md 마지막 갱신일 (60일 초과 warning)
6. slice* brunch가 origin/main에 미반영 (정보성)
7. **외부 자동화 무관여 commit 감지** (audit/nightly 패턴, #71 close 조건 monitoring)

실행 / 출력 / 모드 상세 — 1차 소스: [`scripts/health_check.py` 헤더 docstring](../../scripts/health_check.py)

수동 감지 패턴(`modified` 파일, 자동 브랜치 전환 등)과 대응 — 1차 소스: [`operational_guide.md` §충돌 감지 시 대응](../portfolio/coach/operational_guide.md)

---

## 5. Layer 1~4 로드맵

| Layer | 시점 | 작업 | 상태 |
|-------|------|------|------|
| **1** (즉시) | 2026-05-28 | `scripts/health_check.py` 도입 + PROGRESS·DECISIONS·common-bugs 갱신 + Slice 17 closing 후 박음 | ✅ 완료 |
| **2** (단기) | 2026-06-10경 | 1~2주 야간 누적 데이터로 알림 임계 + 채널 결정 | 🟡 대기 |
| **3** (중기) | 운영 안정화 후 | pre-commit hook에 `health_check.py` warning 표시 + GitHub Actions 야간 자동 PR | ⏸ 보류 |
| **4** (장기) | Phase 2 진입 시 | PROGRESS 자동 추출 영역을 `make progress`로 완전 자동화 | ⏸ 보류 |

각 Layer 의도 + Why — 1차 소스: [DECISIONS.md "Layer 1~4 채택"](../../DECISIONS.md)

---

## 6. 단계 2 진입 일정 (2026-06-10)

- **트리거**: `docs/nightly_auto_system/YYYYMM/DD/health_check.json` 1~2주 누적 후 분석
- **결정 입력값**: 7 항목별 status 분포 / false positive 빈도 / 외부 자동화 commit 감지 정확도
- **결정 산출**: warning 임계 / error 임계 / 알림 채널(이메일·Slack) / Layer 3 진입 시점

상세 진행 메모 — 1차 소스: [`PROGRESS.md` "정합성 / Slice 18 진입 결정"](../../PROGRESS.md)

---

## 7. 잔여 부채 — #71 / #73

| 부채 | 성격 | 상태 |
|------|------|------|
| **#71** 외부 자동화의 slice15 history 오염 | 환경/자동화 (코드 아님) | 조건부 close (Slice 17) — Slice 16+17 무재발 + iron-trading 폴더 분리 회피책. **근본 해결 아님**, 환경 변경 시 재점검 |
| **#73** pre-commit hook 화이트리스트 슬라이스마다 수동 추가 | 편의 부채 | open (PS 0.5, 안 A regex 패턴 / 안 B helper 스크립트 / 안 C 체크리스트 명시 중 택일) |

`#71`의 closing 노트 "환경 변경 시 재점검" 조건은 health_check 7번 항목으로 영구 모니터링되고 있다.

상세 사건 + resolution + 안 A/B/C — 1차 소스: [`docs/portfolio/coach/debts.md` #71·#73](../portfolio/coach/debts.md)

---

## 8. 사고 학습 케이스

Slice 8 Part 1 (2026-05-16) 5건 + Slice 15 Part 2~3 (2026-05-26) 1건 + Slice 17 closing 후 audit commit 1건(`beec905`).

전체 표 — 1차 소스: [`operational_guide.md` §사고 학습 케이스](../portfolio/coach/operational_guide.md) + [`debts.md` #71 history](../portfolio/coach/debts.md)

---

## 관련 1차 소스

| 영역 | 1차 소스 |
|------|---------|
| Session Lifecycle | [`CLAUDE.md` §Harness Protocol](../../CLAUDE.md) |
| 정합성 결정 + Layer 1~4 | [`DECISIONS.md` §문서·git 정합성 관리 원칙](../../DECISIONS.md) |
| 현재 상태 + 단계 2 일정 | [`PROGRESS.md` §정합성 문제 발견 + 다음 세션에서 할 일](../../PROGRESS.md) |
| 시간대 정책 + 다층 방어 | [`docs/portfolio/coach/operational_guide.md`](../portfolio/coach/operational_guide.md) |
| 부채 #71·#73 상세 | [`docs/portfolio/coach/debts.md`](../portfolio/coach/debts.md) |
| 검증 스크립트 | [`scripts/health_check.py`](../../scripts/health_check.py) |
| 야간 v3 스크립트 | [`docs/infra/nightly_v3.sh`](../infra/nightly_v3.sh) |
| 버그 패턴 정리 | [`sub_claude_md/common-bugs.md` #30](../../sub_claude_md/common-bugs.md) |
| 세션 시작 진입점 | [`docs/harness/SESSION_STARTUP_CHECKLIST.md`](SESSION_STARTUP_CHECKLIST.md) |

> **이중 진실의 소스 방지 약속**: 본 문서가 1차 소스의 내용을 복제하기 시작하면 즉시 trim. 본 문서는 항상 "어디로 가야 하는가"의 지도일 뿐.
