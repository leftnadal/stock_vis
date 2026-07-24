# 병진 야간 창 명령서: verify launchd repoint 전파 + plist 교체

- 대상: 병진(사용자) 수동 실행. CC는 명령 제시·사후 판정만.
- 근거: [개정문1](verify_launchd_repoint_amendment1.md) + [개정문2](verify_launchd_repoint_amendment2.md). 원 지시서 §2-2/§2-3 승계.
- 목적: 라이브 verify(02:30)를 origin/main 추적 트리(sv-worker-runtime)로 repoint. self-locate 래퍼는 이미 origin/main 착지(`b9ddf41a`).
- 성격: **라이브 3종 재기동(celery-worker + celery-beat + daphne/WS 끊김) 포함.** 단일 야간 창에서 한 번에.

---

## ⏱ 창 선택 (반드시 먼저)

- **금지 구간**: 23:00–03:30 KST(nightly 자동화 23:00 + 최대 4h, 그리고 verify 02:30 근접). 이 구간을 피한다.
- 권장: 밤 22:30 이전 종료 가능한 시각, 또는 nightly 완료 확인 후(03:30+ ~ 다음 22:00). 라이브 사용자 적은 시각.

## STEP A — 사전 점검 게이트 (겹치면 대기, 진행 금지)

```bash
UID_NUM=$(id -u)
VENV_BIN="/Users/byeongjinjeong/Library/Caches/pypoetry/virtualenvs/stock_javis_system-_jE0wOmK-py3.12/bin"

# A-1. 현재 시각이 금지구간(23:00–03:30 KST) 밖인가
TZ=Asia/Seoul date '+%Y-%m-%d %H:%M %Z'

# A-2. nightly 자동화가 지금 돌고 있지 않은가 (PID가 있으면 실행 중 → 대기)
launchctl print gui/$UID_NUM/com.stockvis.nightly 2>/dev/null | grep -E 'state = |pid = '

# A-3. in-flight Celery task 유무 (active가 비어있어야 안전. task 있으면 완료 대기)
"$VENV_BIN/celery" -A config inspect active --timeout 8
```

- **판정**: A-1 금지구간 밖 + A-2 state=not running(pid 없음) + A-3 active 태스크 없음(빈 목록) → STEP B 진행. 하나라도 실패 → **대기 후 재점검**.

## STEP B — worker_sync 전파 (self-updating 엔트리포인트)

`sv sync`는 worker 트리를 origin/main으로 먼저 최신화한 뒤 worker_sync.sh를 exec한다(stale 사본 실행 방지). 3트리 re-detach + 재기동을 수행한다.

```bash
~/bin/sv sync 2>&1 | tee ~/Library/Logs/stockvis/repoint_sync_$(date +%Y%m%d_%H%M).log
```

기대 출력: `worker 트리 re-detach: b9ddf41a`(또는 그 이후 origin/main) · `celery-worker·celery-beat 재기동 완료` · `✓ celery worker 응답` · `api 트리 re-detach` · `daphne 재기동 완료` · `✓ daphne 응답`.

### B-검증 (GREEN이어야 STEP C로) — 같은 shell 재조회

```bash
# sv-worker-runtime 래퍼에 self-locate가 실제 반영됐는지 파일 내용으로 확증
grep -n 'PROJECT_DIR' /Users/byeongjinjeong/worktrees/sv-worker-runtime/scripts/verify-pair.sh
git -C /Users/byeongjinjeong/worktrees/sv-worker-runtime rev-parse --short HEAD
git -C /Users/byeongjinjeong/worktrees/sv-worker-runtime rev-parse --short origin/main
```

- **GREEN 조건**: `PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"` 가 보이고(하드코딩 `/Desktop/stock_vis` 아님), HEAD == origin/main.
- **실패 시**: STEP C 진행 금지. `sv sync` 재실행 1회. 그래도 미반영이면 **중단** 후 회부(원복 불필요 — plist 미변경 상태).

## STEP C — plist 교체 (§2-2)

### C-1. 백업 (원복 근거)

```bash
cp ~/Library/LaunchAgents/com.stockvis.verify-pair.plist \
   ~/Library/LaunchAgents/com.stockvis.verify-pair.plist.pre_repoint_backup
ls -la ~/Library/LaunchAgents/com.stockvis.verify-pair.plist.pre_repoint_backup
```

### C-2. 후보 plist 생성 (현행 → 2필드만 교체: ProgramArguments 래퍼 경로 + WorkingDirectory)

```bash
P=~/Library/LaunchAgents/com.stockvis.verify-pair.plist
sed -i '' 's#/Users/byeongjinjeong/Desktop/stock_vis/scripts/verify-pair.sh#/Users/byeongjinjeong/worktrees/sv-worker-runtime/scripts/verify-pair.sh#' "$P"
sed -i '' 's#<string>/Users/byeongjinjeong/Desktop/stock_vis</string>#<string>/Users/byeongjinjeong/worktrees/sv-worker-runtime</string>#' "$P"
# 확인: 아래 diff가 정확히 2줄(11 ProgramArguments · 15 WorkingDirectory)만 바뀌어야 함
diff ~/Library/LaunchAgents/com.stockvis.verify-pair.plist.pre_repoint_backup "$P"
```

기대 diff (정확히 이 2줄만):
```
11c11
<         <string>/Users/byeongjinjeong/Desktop/stock_vis/scripts/verify-pair.sh</string>
---
>         <string>/Users/byeongjinjeong/worktrees/sv-worker-runtime/scripts/verify-pair.sh</string>
15c15
<     <string>/Users/byeongjinjeong/Desktop/stock_vis</string>
---
>     <string>/Users/byeongjinjeong/worktrees/sv-worker-runtime</string>
```

- **2줄 초과/불일치 시**: 즉시 중단 → **원복**(아래 R) 후 회부.

### C-3. 재적재 (bootout → bootstrap)

```bash
UID_NUM=$(id -u)
launchctl bootout gui/$UID_NUM/com.stockvis.verify-pair 2>/dev/null || true
launchctl bootstrap gui/$UID_NUM ~/Library/LaunchAgents/com.stockvis.verify-pair.plist
launchctl print gui/$UID_NUM/com.stockvis.verify-pair | grep -E 'state|program|arguments|/verify-pair.sh|sv-worker-runtime' 
```

- **§2-3 실효 경로 판정**: `launchctl print` 출력의 arguments/path가 `…/sv-worker-runtime/scripts/verify-pair.sh`를 가리켜야 함. `Desktop/stock_vis`가 남아 있으면 재적재 실패 → **원복**.

## STEP D — 수동 verify 1회 발화 (행위보존 + section D 육안)

```bash
LOG=~/Library/Logs/stockvis/verify_repoint_manual_$(date +%Y%m%d_%H%M).log
launchctl kickstart -k gui/$(id -u)/com.stockvis.verify-pair
sleep 20
tail -n 120 ~/Library/Logs/stockvis/verify-pair.log | tee "$LOG"
```

- **육안 1차 확인 2줄** (정밀 IDENTICAL 비교는 익일 회수 세션이 이 `$LOG`로 수행):
  1. PRE/A/B/C 섹션 출력이 존재하는가 (기존 4섹션 형식 보존).
  2. section D 3항목(조상기반 drift · stale 마커 · 코드버전) 출력이 **존재**하는가 (`drift/marker/codever` 라인).
- section D가 나타나면 = repoint 성공(라이브 트리가 origin/main 코드 실행). 로그 경로를 회수 세션에 전달.

## ⛔ 이 창에서 금지

- **§3-2(인위 stale 마커 발화 테스트) 실행 금지** — 익일 02:30 봉인 관찰 후 회수 세션에서 실행(봉인 관찰 오염 방지, 개정문2).
- Desktop 공유 트리 쓰기 접촉 금지. 범위 밖 파일 접촉 발생 시 중단.

## R — 원복 명령 (임의 STEP 실패 시)

```bash
UID_NUM=$(id -u)
# plist 백업 복원
cp ~/Library/LaunchAgents/com.stockvis.verify-pair.plist.pre_repoint_backup \
   ~/Library/LaunchAgents/com.stockvis.verify-pair.plist
# 재적재 원상
launchctl bootout gui/$UID_NUM/com.stockvis.verify-pair 2>/dev/null || true
launchctl bootstrap gui/$UID_NUM ~/Library/LaunchAgents/com.stockvis.verify-pair.plist
launchctl print gui/$UID_NUM/com.stockvis.verify-pair | grep -E '/verify-pair.sh'
```

- worker_sync(STEP B)는 트리를 origin/main으로 정렬한 것뿐 = 원복 불필요(정상 상태). plist만 원복하면 repoint 이전과 동일 거동(공유트리 구버전 verify).

## 완료 보고 (회수 세션 인계용)

- STEP A~D 각 출력 로그 경로 · C-2 diff 2줄 확인 · D 육안 2줄 판정
- 익일 02:30 라이브 관찰 예약 1행 (첫 section D 3항목 발화 관찰 = Phase 3 봉인)
