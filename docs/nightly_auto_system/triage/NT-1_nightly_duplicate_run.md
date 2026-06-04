# NT-1 — 야간 자동화 중복 실행 진단·단일화 (ops 풀 지시서)

- **등록일**: 2026-06-04
- **출처보고서**: `~/Desktop/stock_vis/docs/nightly_auto_system/reports/6월/3일/` (보고서 22개 = 11종 ×2 흔적)
- **분류**: ops-scoped (nightly 자동화 자체 / 정합성)
- **심각도**: HIGH (보고서 신뢰도 영향, 야간 LLM 비용 2배 가능성)
- **baseline**: 🆕신규
- **목적지**: ops 풀 지시서 (본 문서)

---

## 한 줄 문제

야간 보고서가 단일 회차여야 하는데 11종 × 2 = 22개로 떨어졌다. 첫 배치 12종(`api_dependency_audit` ~ `security_audit`) + 두 번째 10종(`performance_audit`·`security_audit` 누락)으로, **두 번째 실행이 중간에 잘렸거나 같은 트리거가 2회 호출**됐다.

## 영향

- 동일 보고서 2회 → Gemini API 호출 2배(비용·rate limit 압박)
- baseline 비교 로직(🆕/⬆️/➡️)이 같은 날 두 번째 실행 결과로 갱신되면 의미 손상
- launchd `com.stockvis.nightly` 단독 인지 가정이 깨졌다면 메모리 항목(`project_nightly_automation.md`)도 stale

## STEP 0 — 박지 말고 실측 (조치 전 필수)

다음을 **순서대로** 확인하고 결과를 본 문서 하단 "STEP 0 결과" 섹션에 기록한다.

1. **launchd 등록 현황**
   ```bash
   launchctl list | grep -i stockvis
   ls -la ~/Library/LaunchAgents/ | grep -i stockvis
   ```
   - 기대: `com.stockvis.nightly` 1건만 활성.
   - 의심: 같은 작업이 2개 plist로 등록됐을 수 있다(예: `.nightly` + `.nightly_v2`).

2. **cron 등록 현황**
   ```bash
   crontab -l 2>/dev/null | grep -iE 'nightly|stock_vis|stock-vis'
   sudo crontab -l 2>/dev/null | grep -iE 'nightly|stock_vis|stock-vis'
   ```
   - 기대: 비어 있음(launchd가 단일 트리거).
   - 의심: launchd 도입 전 cron 항목이 남아있을 가능성.

3. **launchd plist 실 트리거 시각**
   ```bash
   plutil -p ~/Library/LaunchAgents/com.stockvis.nightly.plist | grep -A2 -i 'StartCalendarInterval\|StartInterval'
   ```
   - 어제(6/3) 보고서가 두 회차로 떨어진 시각 차를 보고서 mtime으로 확인:
     ```bash
     stat -f "%Sm %N" docs/nightly_auto_system/reports/6월/3일/* | sort
     ```

4. **nightly_v3.sh 진입 가드**
   - `nightly_v3.sh` 첫 줄에 **중복 실행 방지 lock**(`flock` / pidfile)이 있는지 확인.
   - 없다면 같은 시각 두 트리거가 동시에 들어와도 막을 방법이 없다.

5. **watchdog 항목**
   - 메모리 `project_operations_infra_2026-05.md`에 "watchdog 중복감지" 언급이 있다 → 실제 watchdog 스크립트 위치 확인:
     ```bash
     find ~/stock-vis-nightly -name '*watchdog*' 2>/dev/null
     find ~/Library/LaunchAgents -name '*watchdog*' 2>/dev/null
     ```
   - watchdog이 떠 있는데 중복 트리거를 못 잡았다면 watchdog 로직 자체 점검 필요.

## 조치 — STEP 0 결과별 분기

### 경우 A: cron + launchd 동시 등록 (가능성 1순위)
- **조치**: cron 항목 제거 (launchd가 표준).
  ```bash
  crontab -l > /tmp/crontab.bak.$(date +%Y%m%d)
  crontab -e  # nightly 관련 줄 삭제
  ```
- **검증**: 다음 야간 회차에서 보고서 11종(혹은 정상 N종) 1회만 생성되는지 확인.

### 경우 B: launchd plist 2개 (`.nightly` + `.nightly_v2`)
- **조치**: 신규 plist 1개만 유지, 구 plist unload + 파일 백업 후 제거.
  ```bash
  launchctl unload ~/Library/LaunchAgents/com.stockvis.nightly_old.plist
  mv ~/Library/LaunchAgents/com.stockvis.nightly_old.plist ~/stock-vis-nightly/_archive/
  ```

### 경우 C: 단일 launchd인데 두 번 실행됨 (수동 1회 + 자동 1회 가능성)
- **조치 없음**(우발적 실행). 단, `nightly_v3.sh` 진입 가드 부재가 확인되면 **NT-1b 후속 PR**:
  - 스크립트 첫머리에 `flock` 또는 pidfile 가드 추가:
    ```bash
    LOCK=/tmp/stockvis_nightly.lock
    exec 9>"$LOCK"
    flock -n 9 || { echo "[nightly] 이미 실행 중 — 종료"; exit 0; }
    ```
  - 이 부분은 **사용자 손**(`nightly_v3.sh`는 git 밖이라 Claude Code 무수정 — 본 지시서에 패치 텍스트만 제공).

### 경우 D: 야간 트리거는 1회인데 보고서 생성 단계가 내부에서 두 번 도는 구조
- `nightly_v3.sh` 안 보고서 생성 루프(`for audit in ...; do ... done`) 중복 호출 여부 점검.
- 사용자 손으로 스크립트 진단 + 본 문서에 회신.

## 행위보존 제약

- launchd plist 수정 시 `StartCalendarInterval` 시각 변경 금지(기존 02:00/07:00 KST 운영 시간 유지).
- 보고서 디렉토리(`reports/<월>/<일>/`)는 손대지 않는다 — baseline 비교 데이터 손실 위험.

## 검증 (조치 후 1회차)

1. 야간 회차 완료 후 보고서 디렉토리 파일 수 확인:
   ```bash
   ls docs/nightly_auto_system/reports/<당월>/<당일>/ | wc -l
   ```
   - 기대: 정상 보고서 수(STEP 0의 mtime 비교에서 추정한 단일 회차 N).
2. Daily Report 메일 본문의 "🌙 야간 자동화 보고서 → 생성 보고서 수" 값 확인.

## 롤백

- launchd plist 수정만 했다면 `launchctl unload` + 백업 plist `launchctl load`로 즉시 원복.
- cron 라인 제거했다면 `/tmp/crontab.bak.*`에서 복구.
- `nightly_v3.sh` 가드 패치는 사용자 손 → 수동 revert.

## 완료 조건

- [ ] STEP 0 결과 본 문서에 기록.
- [ ] 분기(A/B/C/D) 확정 + 조치 적용.
- [ ] 다음 야간 회차에서 보고서 단일 생성 확인.
- [ ] `project_nightly_automation.md` 메모리 항목 갱신(현재 트리거 단일화 사실).
- [ ] TASKQUEUE.md NT-1 상태 `완료` + 처리 커밋 해시 기록.

---

## STEP 0 결과 (2026-06-04 실측)

**launchctl**:
- `com.stockvis.nightly`(미실행 상태 표기 `-`, 23:00 트리거 대기 정상)
- 워커 3개(`celery-worker`, `celery-worker-neo4j`, `celery-watchdog`) + `pg-backup` + `celery-beat` 모두 등록.
- LaunchAgents 디렉토리에 nightly plist 1건만 (`com.stockvis.nightly.plist`, May 22 18:54).

**crontab**: 비어 있음 (cron 중복 없음). sudo cron은 권한상 미확인(사용자 손, 기대=비어 있음).

**plist trigger**:
- `StartCalendarInterval`: Hour=23, Minute=0 (KST 23:00) — 단일 트리거.
- 실 호출: `/bin/bash -c "..."` → `$NIGHTLY_DIR/run_tier3_audits.sh` (NIGHTLY_DIR=`~/stock-vis-nightly`).
- ⚠️ **`nightly_v3.sh`는 plist에서 호출되지 않는다.** 3 worktree에 동일 파일 존재(git tracked, diff 차이 없음)하지만 실제 실행은 `run_tier3_audits.sh`.

**`run_tier3_audits.sh` 구조**:
- `run_audit` 호출 = **12회** (작업 15 / 16 / 17 / 14 / 6 / 20 / 10 / 9 / 18 / 19-A / 19-B / 19-C).
- 보고서 출력 경로: `docs/nightly_auto_system/reports/$(date +%-m월)/$(date +%-d일)/<name>.md`.
- 한 회차당 보고서 정확히 12개 생성.

**6/3 보고서 파일 실측**:
- 파일 수: **12개** (run_audit 호출 수와 1:1 매칭).
- btime = mtime = ctime 모두 23:05:37 ~ 00:08:41 단조 증가, 덮어쓰기 흔적 없음.
- inode 12개 모두 고유, 심볼릭/하드 링크 없음.

**메일이 보여준 22행의 정체**:
- 메일 첫 12행 줄 수와 실제 파일 줄 수를 매핑:
  - 첫 10행(api_dependency=217 ~ remaining=196) = **6/2 보고서 줄 수**와 일치.
  - 11~12행(performance=261, security=233) = **6/3 보고서 줄 수**와 일치.
  - 두 번째 10행(api_dependency=186 ~ remaining=248) = **6/3 보고서 줄 수**와 일치.
- 즉 야간 회차는 단일 정상. 메일 본문 생성기가 **6/2 일부 + 6/3 전체를 합쳐 22행으로 표기**한 표시 버그.

**flock 가드**: `run_tier3_audits.sh` 첫머리에 `flock`/pidfile 없음. 단, 단일 회차 확인됐으므로 즉시 필요는 낮음.

**watchdog**: `com.stockvis.celery-watchdog` 등록 활성. 메모리 `project_operations_infra_2026-05.md`의 "중복감지" 항목과 일치.

## 결정 분기

**경우 E (신규 — STEP 0 결과)**: 야간 자동화는 단일 회차 정상 동작. 메일 본문 생성 로직(보고서 카운트·목록 표시)이 6/2 일부 + 6/3 전체를 합쳐 표기하는 표시 버그.

**조치**:
1. **NT-1을 재분류**: "야간 자동화 중복 실행" → "**메일 본문 표시 버그**".
2. **NT-1 본 결정의 처리 책임은 사용자 손 영역** — `~/stock-vis-nightly/run_tier3_audits.sh` 또는 메일 본문 생성 스크립트(보고서 목록 출력 부분)가 git 밖이거나 ops 자동화 영역이라 Claude Code 무수정 정책 적용(setup 문서 결정 ⑤).
3. **ops 후속**:
   - 메일 본문 생성 로직 점검 권장(사용자 손). 후보 위치:
     - `~/stock-vis-nightly/run_tier3_audits.sh` 마지막 단(메일 발송 직전 보고서 목록 빌드)
     - 또는 별도 메일 본문 빌더가 `find reports/ -mtime -2`로 어제+오늘 합쳐서 출력하는 패턴
   - 패치 가설: 보고서 목록 빌드 시 **`reports/<오늘 월>/<오늘 일>/` 디렉토리에 한정**하도록 `find` 범위 좁히기.
4. **NT-1b 후속 권장(별도 트랙)**: `flock`/pidfile 가드를 `run_tier3_audits.sh`에 추가 — 현재 단일 회차지만 우발적 두 번 트리거 방어용. 사용자 손 패치.

**적용 커밋/명령**: 본 STEP 0 결과 박음 (`docs/nightly_auto_system/triage/NT-1_nightly_duplicate_run.md` 갱신).

**경우 A/B/C/D는 모두 미해당** — cron 비어있고, plist 단일이며, 보고서 덮어쓰기 없음, 트리거 1회 정상.

## 후속 조치 (TASKQUEUE)

- NT-1 상태: `라우팅됨` → **`완료 (보고)`** (자동화 자체 이상 없음, 메일 표시 버그는 사용자 손 트랙으로 이관).
- DECISIONS.md에 결론 박음: "NT-1은 자동화 정상, 메일 본문 표시 버그로 재분류".
