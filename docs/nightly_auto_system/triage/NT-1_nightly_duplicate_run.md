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

## STEP 0 결과 (실행 후 채움)

> 실측 결과를 여기에 붙인다.

```
launchctl: 
crontab: 
plist trigger: 
mtime 차이: 
flock 가드 유무: 
watchdog: 
```

## 결정 분기

> 경우 A/B/C/D 중 어디인지 + 적용 조치.

```
경우: 
조치: 
적용 커밋/명령: 
```
