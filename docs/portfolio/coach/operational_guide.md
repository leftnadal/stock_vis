# 운영 가이드 — Stock-Vis Portfolio Coach 작업 정책

> **작성일**: 2026-05-17 (Slice 8 Part 2 Step 0, #42 close)
> **적용 범위**: 모든 Portfolio Coach 작업 (Slice 8 이후)

---

## 작업 환경 전제

- **Source of truth**: `/Users/byeongjinjeong/Desktop/stock_vis`
- **iCloud 복사본**: `~/Library/Mobile Documents/com~apple~CloudDocs/Desktop/stock_vis/` (백업용, 작업 금지, `DO_NOT_EDIT_USE_DESKTOP.md` 표지)
- **pre-commit hook**: `.git/hooks/pre-commit` (#39, 브랜치 화이트리스트 검증)
- **확인 표지**: 루트의 `WORKSPACE_ROOT.md` (Slice 8 Part 1 Q-1, #38)

---

## 동시 실행 시스템 (인지 필수)

### 야간 자동화 (`com.stockvis.nightly`)

- **위치**: `~/stock-vis-nightly/`
- **launchd label**: `com.stockvis.nightly` (PID 변동)
- **스크립트**: `run_tier1.sh`, `run_tier2_be.sh`, `run_tier2_fe.sh`, `run_tier3_audits.sh`
- **동작**: 동일 working dir(`~/Desktop/stock_vis`)에서 자동 git 작업
  1. `PROJECT_DIR`로 진입
  2. `BASE_BRANCH` 저장 (= 진행 중인 우리 브랜치)
  3. 새 일자별 브랜치 생성 (`test/*-YYYYMMDD`, `fix/*-YYYYMMDD`, `chore/*-YYYYMMDD`)
  4. `claude -p` CLI로 자동 작업 + commit
  5. BASE_BRANCH로 복귀 시도
- **영향**: 우리 commit 직후 working directory의 git HEAD가 자동 전환됨
- **충돌 위험**: edit-time race condition 가능

### Celery 워커 (참고)

- `com.stockvis.celery-worker`, `com.stockvis.celery-beat`, `com.stockvis.celery-watchdog`
- 작업 디렉토리에서 직접 git 동작 안 함 (read-only) → 일반적으로 충돌 없음

---

## I2 정책: 시간대 회피 + 다층 방어

### 작업 시간대

- **권장**: 주간 (09:00 ~ 22:00)
- **금지**: 자정 ~ 새벽 (야간 자동화 활성 시간대)
- **새벽 작업 필요 시**:

  ```bash
  # 일시 중지
  launchctl bootout gui/$(id -u) com.stockvis.nightly

  # 작업 수행 ...

  # 재활성화
  launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.stockvis.nightly.plist
  ```

### 매 작업 시작 시 체크리스트

```bash
pwd                              # /Users/byeongjinjeong/Desktop/stock_vis 확인
git branch --show-current        # 화이트리스트 브랜치 확인 (main/portfolio/slice*)
git status                       # 야간 자동화 흔적 (modified 파일) 확인
git log --oneline -5             # 최근 commit이 의도한 것인지 확인
```

### 매 commit 직후 체크리스트

```bash
git branch --show-current        # 자동 전환 여부 확인 (예상 브랜치인지)
git log --oneline -3             # commit이 의도한 브랜치에 들어갔는지 확인
```

### 충돌 감지 시 대응

| 증상 | 대응 |
|------|------|
| `modified` 파일에 의도하지 않은 변경 발견 | `git stash` 후 점검 |
| 야간 자동화의 commit 발견 | `git log --author` 또는 commit message로 식별, 보존 결정 시 그대로 둠 |
| 자동 브랜치 전환 발견 | `git checkout <원래 브랜치> && git cherry-pick <내 commit>` |
| pre-commit hook 차단 | hook 메시지의 안내대로 `git cherry-pick`으로 작업 이전 |

---

## 다층 방어 설계

| 계층 | 메커니즘 | 차단 시점 |
|------|----------|----------|
| **시스템-time** | 시간대 회피 (자정~새벽 작업 금지) | 작업 시작 전 |
| **edit-time** | `git status` 사전 체크 + WORKSPACE_ROOT 확인 | 편집 직전 |
| **commit-time** | pre-commit hook (브랜치 화이트리스트) | commit 시도 |
| **추적** | reflog + cherry-pick 패턴 | commit 후 복구 |

---

## 부채 추적

| ID | 항목 | 상태 |
|----|------|------|
| #38 | iCloud 표지 (`WORKSPACE_ROOT.md` + `DO_NOT_EDIT_USE_DESKTOP.md`) | close (2026-05-16) |
| #39 | pre-commit hook (브랜치 화이트리스트) | close (2026-05-16) |
| #40 | 야간 자동화 도구 식별 | close (사용자 자체 시스템, 비활성화 보류) |
| #42 | 본 운영 가이드 | close (본 문서, 2026-05-17) |

---

## 사고 학습 케이스

| 일자 | 증상 | 대응 |
|------|------|------|
| 2026-05-16 Slice 8 Part 1 Step 1 | Step 1 #27 commit이 `fix/ts-compile-errors-20260516`로 전환 | `git checkout slice8 + cherry-pick` |
| 2026-05-16 Slice 8 Part 1 Step 2 | Step 2 commit이 `fix/broken-tests-20260516`로 전환 | 동일 |
| 2026-05-16 Slice 8 Part 1 Q-1 | Q-1 commit이 `test/sec-pipeline-tests-20260516`로 전환 | 동일 |
| 2026-05-16 Slice 8 Part 1 Q-2 | hook 활성 후 자체 commit에서 자연 검증 PASS | 자동 차단 동작 확인 |
| 2026-05-16 Slice 8 Part 1 Q-5 | hook이 `test/rag-analysis-unit-tests-20260516`로 전환 차단 | cherry-pick |
| 2026-05-16 Slice 8 Part 1 | 외래 commit `4da2317 test(sec_pipeline)` slice8에 진입 (보존 결정) | 그대로 보존 |

---

## I2 정책 적용 KPI (Slice 8 Part 2 이후 모니터링)

각 슬라이스 종결 시 다음 지표를 추적:

- 야간 자동화 충돌 발생 횟수
- pre-commit hook 차단 횟수
- cherry-pick 대응 횟수
- 외래 commit 진입 건수

지표가 슬라이스당 5건 초과 시 → 야간 자동화 일시 중지 또는 작업 격리 강화 검토 (Slice 9 후보).
