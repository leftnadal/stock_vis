# 상신 — RC-WATCHDOG-DAPHNE-COVERAGE: watchdog 감시 대상에 daphne 추가

- **작성**: 2026-08-31 (CC, ops 소형 세션 · worktree `sv-ops-watchdog-web` / `monorepo/sess-ops-watchdog-web`)
- **변경**: `scripts/celery-watchdog.sh` — `check_service` 호출 1건 추가(실행 라인 +1/-0). 기존 3종 로직 **삭제 라인 0**.
- **성격**: 코드는 main에 랜딩. **런타임 반영(`sv sync`)은 병진 판단** — 아래 §1이 그 판단 재료다.

---

## 0. 한 줄 요지

**배포 범위 문제로 즉시 반영을 권하지 않는다.** `sv sync`는 런타임 트리를 origin/main까지 끌어올리므로 **커밋 16건 + 마이그레이션 4건이 동반**되고, 그중 **`chain_sight` 0034·0035는 prod 미적용**이다. 이 슬라이스 한 줄을 위해 MIG-BUNDLE-1 배포창을 앞당길 이유는 없다. **다음 정규 배포창에 편승**하거나, 급하면 §4의 (b) 단일 파일 반영을 쓴다.

---

## 1. `sv sync` 동반 배포 범위 (병진 판단 재료)

- 런타임 트리 = `1ccb6769` / origin/main = `70d6deec` → **델타 16커밋**

| # | 커밋 | 내용 |
|---|------|------|
| 1 | `0a91488b` | SELFLOOP-DBCONSTRAINT (MIG-BUNDLE-1 A) — a≠b DB 제약 승격 |
| 2 | `53319665` | CS-UNIVERSE-EXCLUDE-FLAG (MIG-BUNDLE-1 B) |
| 3 | `32589f79` | CS-STORY-ACTIVITY-CACHE (MIG-BUNDLE-1 C) |
| 4 | `918604de` | MIG-BUNDLE-1 머지 |
| 5 | `fc83dc71`·`c49e5559` | RC-NEO4J-WORKER-TREE 집행 장부(docs) |
| 6 | `18999078`·`78c6b641` | MIG-BUNDLE-1 C-2 beat 등록 |
| 7 | `b0053927` | union 머지 |
| 8 | `d2bd219b`·`365daefd`·`ab590ef9`·`ccd7e8dd` | EVT-CORR-3 — 재관측 stale→scheduled 복원 |
| 9 | `da0f84af`·`b56f74a8` | MIG-BUNDLE-1 하네스 종결(docs) |
| 10 | `70d6deec` | MGMT-BATCH-40(docs) |

### ⚠️ 동반 마이그레이션 4건 — 2건이 prod 미적용

| 마이그레이션 | prod 적용 |
|---|---|
| `chain_sight.0034_selfloop_db_constraints` | ❌ **미적용** |
| `chain_sight.0035_symbol_story_activity_cache` | ❌ **미적용** |
| `stocks.0017_stock_universe_excluded_flag` | ✅ 2026-08-31 |
| `stocks.0018_flag_leveraged_etfs` | ✅ 2026-08-31 |

> `sv sync`만 하고 `migrate`를 안 하면 **새 코드가 없는 스키마를 참조**할 수 있다. 반대로 `migrate`는 prod DB 쓰기라 별도 승인 사안이다. → **이 슬라이스는 MIG-BUNDLE-1 배포창의 종속물로 다루는 것이 맞다.**

---

## 2. 재등록 불필요 — 실측 근거

`com.stockvis.celery-watchdog` plist 실측: **`KeepAlive` 키 없음** · `RunAtLoad=true` · **`StartInterval=300`** · 현재 `state = not running`(runs=9, last exit 0).

→ 상주 프로세스가 아니라 **주기 실행 잡**이다. launchd가 5분마다 `ProgramArguments`의 bash 스크립트를 **새로 읽어 실행**하므로, 런타임 트리의 파일이 바뀌면 **다음 발화부터 자동으로 새 내용이 돈다**. `bootout`/`bootstrap` **불필요**.

(plist 자체는 이번에 바뀌지 않는다 — 이미 런타임 트리를 가리키고 있다. RC-NEO4J-WORKER-TREE에서 교정 완료.)

---

## 3. 검증 절차 (반영 후)

```bash
# 다음 발화(최대 5분)를 기다린 뒤
tail -20 ~/Library/Logs/stockvis/celery-watchdog.log
```

**합격 기준**: 한 사이클 안에 4종 체크가 모두 돌고, daphne가 살아 있으면 **아무 메시지도 남지 않는다**(정상 시 침묵이 설계). 따라서 다음 중 하나로 확인한다.

- ⒜ daphne 정상 시: `Watchdog check started` → `completed` 사이에 **DOWN/RECOVERED 메시지 없음** (기존과 동일). 이것만으로는 추가분이 도는지 알 수 없으므로 ⒝로 확증.
- ⒝ **확증**: 실행 중인 스크립트가 새 파일인지 직접 확인
  ```bash
  grep -c 'check_service "' ~/worktrees/sv-worker-runtime/scripts/celery-watchdog.sh   # 4 이어야 함
  ```
- ⒞ **동작 확증(선택)**: daphne를 의도적으로 죽여 `Web (daphne) DOWN — launchctl kickstart` 라인과 복구를 관찰. **API 순단이 발생하므로 권장하지 않음**(KeepAlive가 즉시 되살리지만 수 초 공백).

---

## 4. 반영 옵션

| 옵션 | 내용 | 평가 |
|---|---|---|
| **(a) 정공법** | MIG-BUNDLE-1 배포창에서 `sv sync` + `migrate`(chain_sight 0034·0035) | **권장.** 이 슬라이스는 거기에 편승 |
| (b) 단일 파일 | 런타임 트리에서 `git checkout origin/main -- scripts/celery-watchdog.sh` | 즉효이나 **런타임 트리가 dirty**해져 트리 정합 점검·`worker_sync` 가정을 깬다. 급할 때만 |
| (c) 대기 | 다음 정규 배포창까지 유지 | 허용. 감시 공백은 남지만 KeepAlive가 프로세스 사망은 커버 |

---

## 5. 되돌리기

- 코드: main에서 `git revert <이 슬라이스 머지 커밋>` → 다음 `sv sync`에 반영.
- 런타임만 급히 되돌릴 때: 런타임 트리에서 이전 커밋의 파일로 복원 후 다음 발화 대기(재등록 불필요).
- plist 무변경이므로 launchd 조작 불필요.

---

## 6. 범위 밖 — 보고만 (구현 결정 필요)

**2026-08-31 API 다운의 실제 원인은 "프로세스 사망"이 아니라 "잡 언로드"였다.** 이번 추가로도 그 사고는 **완전히 막히지 않는다.**

- 실측 타임라인(`web-error.log`): 11:17:52 기동 → **12:22:26 종료** → 12:34:33 재기동. 약 **12분 다운**. (메모리의 "12:12"는 watchdog의 마지막 neo4j 경보 시각이고, daphne 종료는 12:22가 정확.)
- `com.stockvis.web`은 **`KeepAlive=true`**이고 `daphne-web.sh`가 `exec`로 PID를 유지한다 → **프로세스가 죽으면 launchd가 스스로 되살린다.** 12분이나 다운돼 있었다는 것은 프로세스 사망이 아니라 **잡이 bootout(언로드)된 상태**였음을 뜻한다(그 시각 `launchctl list`에 `com.stockvis.web` 부재를 실측했다).
- 이 경우 watchdog의 `launchctl kickstart`도 **실패**한다 — `Could not find service ... in domain for user gui: 501`(neo4j 워커에서 실증). 즉 **추가된 감시의 실질 효과 = 경보 메일**이고, 복구는 사람이 `bootstrap` 해야 한다.
- **응답 정지(프로세스 생존·무응답)도 못 잡는다.** 현재 방식은 `ps` 문자열 매칭이라 hang을 감지할 수 없다.

→ 완전한 커버리지는 **HTTP 헬스 프로브**(`curl -sf --max-time 3 http://127.0.0.1:18765/api/v1/health/`)와 **잡 언로드 감지**(`launchctl print` 실패 시 `bootstrap` 시도)가 필요하다. 둘 다 이번 지시서 범위 밖이므로 **보고만** 한다. 후속 티켓 후보: `RC-WATCHDOG-HTTP-PROBE`.

---

## 7. 부수 실측 — 유지보수 억제 장치 **없음**

`check_service`는 down 감지 시 **조건 없이** `launchctl kickstart` 한다. 수동 정지 중인 잡을 되살리는 것을 막는 장치(플래그·시간창)가 **없다** — 실제로 RC-A-1 배포창에서 의도적으로 내린 neo4j 워커를 5분마다 되살리려 시도하며 경보를 28회 보냈다.

플래그 파일(`/tmp/stockvis-{label}-{down,duplicate,kicked}`)은 label별로 자동 생성되므로 **daphne 추가로 기존 3종의 플래그가 오염되지는 않는다**(격리 확인).

지시서 §2에 따라 억제 장치는 **추가하지 않았다**(범위 밖). 필요하면 후속 티켓: `RC-WATCHDOG-MAINTENANCE-MUTE`.
