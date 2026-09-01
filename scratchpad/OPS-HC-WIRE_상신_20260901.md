# 상신 — OPS-HEALTHCHECK-NIGHTLY-WIRE: 야간 하네스 건강 점검 launchd 등록

- **작성**: 2026-09-01 (CC, ops 세션 · worktree `sv-ops-hc-wire` / `monorepo/sess-ops-hc-wire`)
- **결정**: 병진 2026-09-01 — **옵션 A(dogfood와 분리된 독립 launchd 잡 + 별도 메일)**. 디렉터 추천은 B(dogfood 편입)였으나 병진이 **격리 최우선**으로 A를 선택.
- **성격**: 코드는 main 랜딩 완료. **launchd 등록만 상신**(서비스 조작 = 자기 집행 금지).

---

## 0. 한 줄 요지

`~/Library/LaunchAgents/com.stockvis.healthcheck.plist`를 bootstrap 하면 매일 **05:40 KST**에 하네스 점검이 돌고, **변화가 있는 날에만** 메일이 온다. **배포창 의존 없음** — 런타임 트리에 이미 코드가 들어갈 조건이 갖춰져 있고(미적용 마이그레이션 0건), `sv sync` 한 번이면 배치된다.

---

## 1. ★ 어제 상신의 전제 정정 (중요)

`RC-WATCHDOG-DAPHNE_상신_20260831.md` §1에서 **"`chain_sight` 0034·0035가 prod 미적용 → MIG-BUNDLE-1 배포창 편승 권고"**라고 썼다. **이 근거는 틀렸다.**

- **원인**: Django 앱 레이블은 **`chainsight`**(언더스코어 없음)인데 디렉터리명 `apps/chain_sight/`를 그대로 써서 `django_migrations`를 조회했다. 존재하지 않는 레이블이라 0행이 나왔고 그것을 "미적용"으로 읽었다.
- **실제**: `chainsight.0034_selfloop_db_constraints`·`0035_symbol_story_activity_cache` 모두 **2026-08-31 적용 완료**. `manage.py showmigrations --plan` 기준 **미적용 마이그레이션 0건**.
- **영향**: RC-WATCHDOG-DAPHNE-COVERAGE의 "배포창 편승 대기"는 **불필요한 보류**였다. `sv sync`를 막을 이유가 없었다.
- **현 상태**: 그 사이 `sv sync`가 실행되어 런타임 트리가 **`9caf9e37`**로 전진했고, **daphne 감시는 이미 라이브**다 — `88f87a48` INCLUDED, 런타임 `celery-watchdog.sh`의 `check_service` **4건**(`Web (daphne)` 포함). watchdog은 StartInterval 잡이라 다음 발화부터 자동 적용됐다. **RC-WATCHDOG-DAPHNE-COVERAGE는 사실상 완료.**
- **교훈**: **디렉터리명 ≠ Django 앱 레이블.** `django_migrations` 조회는 `apps.py`의 `label` 또는 `showmigrations`로 대조할 것. 부정 결과("0행")를 곧바로 "미적용"으로 읽지 말 것 — 조회 자체가 빗나갔을 수 있다.

---

## 2. 배포 경로 — 배포창 의존 **없음**

- 런타임 트리 `9caf9e37` / origin/main `d0114efc` → 델타 **19커밋**, **마이그레이션 0건**.
- 즉 `sv sync` 한 번이면 `auto_agent_system/healthcheck/`가 런타임 트리에 배치된다. migrate 불필요.
- plist는 런타임 트리 경로(`$HOME/worktrees/sv-worker-runtime/auto_agent_system/healthcheck/run_healthcheck.sh`)를 가리키므로 **sv sync가 선행돼야** bootstrap이 의미를 갖는다.

**순서**: ① `sv sync` → ② plist 설치 + bootstrap → ③ 익일 05:40 발화 확인.

> ⚠️ `sv sync` 자체는 워커·beat·daphne 재기동을 동반하므로 **병진 판단 영역**(이 상신의 범위는 ②).

---

## 3. 등록 절차 (병진 수동)

```bash
# ① 코드 배치 확인 (sv sync 이후)
ls -l ~/worktrees/sv-worker-runtime/auto_agent_system/healthcheck/run_healthcheck.sh

# ② plist 설치
cp ~/worktrees/sv-worker-runtime/auto_agent_system/healthcheck/com.stockvis.healthcheck.plist \
   ~/Library/LaunchAgents/com.stockvis.healthcheck.plist
plutil -lint ~/Library/LaunchAgents/com.stockvis.healthcheck.plist

# ③ bootstrap + enable
launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.stockvis.healthcheck.plist
launchctl enable gui/$UID/com.stockvis.healthcheck

# ④ 등록 확인 (05:40 스케줄)
launchctl print gui/$UID/com.stockvis.healthcheck | grep -E "state|Hour|Minute"
```

> **수동 kickstart는 하지 않는다** — 오늘 몫은 이미 수동 실행으로 소진됐고(§4), 같은 날 두 번 돌면 diff 기준일이 흐려진다. **익일 05:40 자연 발화로 검증**한다.

---

## 4. 검증

### 이미 확인된 것 (수동 1회 전체 실행, 2026-09-01 11:19)

- JSON 생성: `~/stock-vis-nightly/health/health_20260901.json` — **list 18건**, 키 `{name, status, status_label, detail, evidence}`, status 분포 `{0: 17, 1: 1}` = **❌0**.
- 메일 **실발송 1통**: `[sent] 첫 수집(baseline) → jinie545@gmail.com`, 제목 `Stock-Vis 하네스 건강 — 9/1 (❌0 ⚠️1)`.
- **런타임 트리 무오염**: 산출물이 전부 `~/stock-vis-nightly` 아래 → `git status` clean 유지(구 wrapper는 트리 내부 `docs/nightly_auto_system`에 썼다).

### 등록 후 확인 (익일 05:40)

```bash
tail -20 $(ls -t ~/stock-vis-nightly/logs/healthcheck_*.log | head -1)
ls -l ~/stock-vis-nightly/health/          # health_YYYYMMDD.json 새 파일
launchctl print gui/$UID/com.stockvis.healthcheck | grep -E "runs|last exit code"
```

**합격 기준**: 새 JSON 1건 생성 · 로그에 `✅ 완료` · `runs ≥ 1`. 메일은 **변화가 없으면 오지 않는 것이 정상**(§5) — 9/2는 화요일이라 조용하면 미발송이 맞다. 다음 월요일(9/7)에는 이상이 없어도 1통 온다.

---

## 5. 발송 규칙 (노이즈 방지)

옵션 A는 "메일 2통"이 단점이므로 다음 규칙으로 보완했다.

| 조건 | 발송 |
|---|---|
| 첫 수집(baseline) | ✅ |
| ERROR ≥ 1 | ✅ |
| 신규 이상 발생 | ✅ |
| 해소 발생 | ✅ |
| **월요일** (이상 없어도) | ✅ — 잡이 죽은 것과 조용한 것을 구별 |
| 그 외(변화 0 · ERROR 0) | ❌ **미발송** |

같은 WARN이 계속 이어지는 것만으로는 보내지 않는다(재발 WARN은 조용히 누적, 메일에는 `[재발 N일째]`로 표기).

---

## 6. 되돌리기

```bash
launchctl bootout gui/$UID/com.stockvis.healthcheck
rm ~/Library/LaunchAgents/com.stockvis.healthcheck.plist
```

코드 롤백이 필요하면 main에서 `git revert <머지 커밋>` 후 `sv sync`. 산출물(`~/stock-vis-nightly/health/`)은 트리 밖이라 남겨도 무해하다.

---

## 7. 선반영 대안 (후보 — 실행 금지)

`sv sync` 없이 이 디렉터리만 런타임 트리에 넣는 방법:

```bash
cd ~/worktrees/sv-worker-runtime && git checkout origin/main -- auto_agent_system/healthcheck auto_agent_system/common
```

- **장점**: 워커·daphne 재기동 없이 즉시 배선.
- **단점**: 런타임 트리가 **dirty**해져 `worker_sync`의 트리 정합 가정과 `H-LAUNCHD-TREE`의 전제를 깬다. detached HEAD에 추적 변경이 남으면 다음 `sv sync`의 `git checkout`이 충돌하거나 조용히 덮어쓴다.
- **판정**: **비권장.** `sv sync`가 마이그레이션 장벽 없이(§2) 가능하므로 정공법을 쓴다. 기록만 남긴다.
