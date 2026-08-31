# 상신 — RC-NEO4J-WORKER-TREE: launchd 실행 트리 교정

> ✅ **STEP 0 완료 @`9a17e324`** (래퍼 3건 self-locate 교정 랜딩, RC-EXEC-TREE-LAND) — **`sv sync` 후 ① 진행 가능.**

- **작성**: 2026-08-31 (CC, ops 소형 세션 · worktree `sv-ops-plist-tree` / `monorepo/sess-ops-plist-tree`)
- **성격**: **상신 전용.** launchd 편집·bootout/bootstrap·서비스 기동은 CC가 집행하지 않는다([[feedback_service_op_submit_not_execute]]). 아래 절차는 병진이 수동 실행.
- **측정 기준시각**: 12:31~12:35 KST

---

## 0. 한 줄 요지

celery-worker-neo4j 결함은 **단건이 아니라 부류**다. plist 3건(`celery-worker-neo4j` / `celery-watchdog` / `pg-backup`)이 `~/Desktop/stock_vis`를 가리키고, **더 근본적으로는 래퍼 스크립트 3건이 `PROJECT_DIR`을 Desktop으로 하드코딩**하고 있어 **plist만 고쳐도 무효**다. plist + 스크립트를 함께 교정해야 한다.

---

## 1. plist 전수 점검 (12건)

| # | Label | 실행 트리 (WorkingDirectory / 스크립트) | 로드 상태(12:35) | 판정 |
|---|-------|------------------------------------------|------------------|------|
| 1 | `com.stockvis.celery-worker-neo4j` | **Desktop/stock_vis** (양쪽 다) | 미로드 (정지 유지) | ❌ **결함 A — 쓰기 워커** |
| 2 | `com.stockvis.celery-watchdog` | **Desktop/stock_vis** (양쪽 다) | 미로드 | ❌ **결함 B — 재기동 유발** |
| 3 | `com.stockvis.pg-backup` | **Desktop/stock_vis** (양쪽 다) | 로드·대기(02:00) | ❌ **결함 C — 읽기(.env 참조)** |
| 4 | `com.stockvis.celery-worker` | `sv-worker-runtime` | 실행 pid 81152 | ✅ |
| 5 | `com.stockvis.celery-beat` | `sv-worker-runtime` | 실행 pid 81154 | ✅ |
| 6 | `com.stockvis.runtime-check` | `sv-worker-runtime` | 로드·1h 주기 (last exit 2) | ✅ 트리 정합 (종료코드는 별건) |
| 7 | `com.stockvis.verify-pair` | `sv-worker-runtime` (스크립트는 self-locate) | 미로드 | ✅ **모범 패턴** |
| 8 | `com.stockvis.cn_repair.nightly` *(`.disabled-20260811`)* | `sv-worker-runtime` | 비활성 파일 | ✅ |
| 9 | `com.stockvis.web` (daphne) | `sv-api-runtime` | 실행 pid 81157 | ✅ |
| 10 | `com.stockvis.web-frontend` | `sv-web-runtime/frontend` | 실행 pid 70692 | ✅ |
| 11 | `com.stockvis.dogfood` | `$HOME/worktrees/sv-worker-runtime` (참조 모델) | 로드·05:20 | ✅ |
| 12 | `com.stockvis.nightly` | `$HOME/stock-vis-nightly` (repo 트리 아님) | 로드·23:00 | ✅ 해당 없음 |
| — | `com.stockvis.neo4j` | `~/neo4j` (DB 엔진, repo 무관) | 실행 pid 77030 | ✅ 해당 없음 |

### 1-1. 래퍼 스크립트 하드코딩 (근본 원인)

`~/worktrees/sv-worker-runtime/scripts/` 기준 `PROJECT_DIR` 정의:

| 스크립트 | PROJECT_DIR | 판정 |
|----------|-------------|------|
| `celery-worker-neo4j.sh` | `"/Users/byeongjinjeong/Desktop/stock_vis"` | ❌ |
| `celery-watchdog.sh` | `"/Users/byeongjinjeong/Desktop/stock_vis"` | ❌ |
| `pg-backup.sh` | `"/Users/byeongjinjeong/Desktop/stock_vis"` | ❌ |
| `celery-worker.sh` | `".../worktrees/sv-worker-runtime"` | ✅ (절대·정합) |
| `celery-beat.sh` | `".../worktrees/sv-worker-runtime"` | ✅ (절대·정합) |
| `daphne-web.sh` | `".../worktrees/sv-api-runtime"` | ✅ (의도) |
| `runtime-check.sh` | `".../worktrees/sv-worker-runtime"` | ✅ |
| `verify-pair.sh` | `$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)` | ✅ **self-locate 선례**(OPS-VERIFY-EXEC-TREE 개정문1) |

> ⚠️ **핵심**: `celery-worker-neo4j.sh`는 스스로 `cd /Users/byeongjinjeong/Desktop/stock_vis` 한다. plist의 `WorkingDirectory`/스크립트 경로만 런타임 트리로 바꿔도 **래퍼가 다시 Desktop으로 cd** 하므로 구 코드가 실행된다. **§2의 스크립트 diff가 필수 동반**.

### 1-2. 후보(이번 범위 밖, 등재만)

- `scripts/worker_sync.sh:31` `SHARED_SIGNALS="/Users/byeongjinjeong/Desktop/stock_vis/frontend/public/static/signals"` — EOD 시그널 baking 산출물의 공유 원본으로 **의도된 것일 수 있음**. 판단 유보, TASKQUEUE 후보 등재.
- `scripts/hooks/pre-commit:38` `EXPECTED_PATH="/Users/byeongjinjeong/Desktop/stock_vis"` — 훅의 의도적 가드(공유 본체 커밋 차단). 결함 아님.

---

## 2. 런타임 트리 안전 게이트 — RC-A-1 v3.0 포함 여부

`~/worktrees/sv-worker-runtime`: HEAD `8cfbcabb` (detached), 작업트리 clean, `origin/main`과 **0 behind / 0 ahead**.

| 커밋 | 내용 | 판정 |
|------|------|------|
| `a396e748` | D-RC-DECAY-SEMANTIC — 감쇠 타입 게이트 | **INCLUDED** |
| `23318e25` | **D-RC-SCALE — 점수 눈금 [0,100]→[0,1] + score_version 3.0** | **INCLUDED** |
| `4efdc4c9` | D-RC-PC-DISPOSE — PRICE_CORRELATED 처분 커맨드 | **INCLUDED** |
| `0d414e62` | RC-A-1 PART 4 하네스 | **INCLUDED** |
| `c8dfc627` | RC-A-1 배포창 ②~⑥ 완주 | **INCLUDED** |

→ **안전 게이트 §1-2 충족.** 런타임 트리에서 기동하면 v3.0 눈금 코드가 돈다.

---

## 3. neo4j 동기 밀림 규모 (read-only)

- **실효 밀림 = 0건.** `sync_dirty_to_neo4j`의 실제 대상(`current()` + `target_symbol_id IS NOT NULL`) 기준 dirty **0건**.
- `sec_supply_chain_evidence.neo4j_dirty = true` 원시 2,831행이 있으나 **전량 `target_symbol_id IS NULL`**(티커 미매칭) → 동기 대상이 아님. (v1 1,437 / v2 1,394)
- `chainsight_chain_profile` dirty 0 (최종 동기 08-30 01:00), `chainsight_relation_confidence` dirty 0 (최종 동기 08-31 01:30).
- 워커 정지 직전 로그(09:15·09:20)도 `sync_dirty_to_neo4j: no dirty rows` — 일치.
- **Redis `neo4j` 큐에 태스크 메시지 28건 적체** (beat가 5분마다 발송, 워커 09:34 종료 이후). 워커 기동 시 28회 연속 no-op으로 즉시 소진 예상 — 무해하나 로그에 나타남.

> 결론: **정지 유지의 데이터 비용은 현재 0**. 서두를 이유는 없고, 교정 완결 후 기동해도 손실 없음.

---

## 4. 집행 절차 (병진 수동)

### 🚦 안전 게이트 (③ 진행 전 필수)

> **"런타임 트리 커밋이 RC-A-1 v3.0을 포함(본 문서 §2에서 확인: `23318e25` INCLUDED, origin/main과 0/0)한 것을 재확인한 뒤에만 ③ bootstrap을 진행한다."**
>
> 재확인 명령:
> ```bash
> cd ~/worktrees/sv-worker-runtime && git rev-parse --short HEAD && \
>   git merge-base --is-ancestor 23318e25 HEAD && echo "v3.0 INCLUDED — 게이트 통과" || echo "HALT"
> ```
> 추가 게이트: **스크립트 교정(§4 STEP 0)이 런타임 트리에 반영된 뒤에만** ③ 진행. 미반영 상태로 기동하면 래퍼가 Desktop으로 cd → 구 눈금 코드 실행(= 이번 사고 재현).

### STEP 0 — 스크립트 교정 랜딩 (선행 필수)

```bash
# 초안 diff: scripts/ops/launchd/exec-tree-selflocate.diff.proposed
cd <main 체크아웃 트리> && git apply scripts/ops/launchd/exec-tree-selflocate.diff.proposed
# 리뷰 → 커밋 → main 머지 → 런타임 트리 갱신
cd ~/worktrees/sv-worker-runtime && git fetch origin main && git checkout <새 main SHA>
grep -n 'PROJECT_DIR=' scripts/celery-worker-neo4j.sh   # self-locate 확인
```

### ① bootout (기존 정의 제거)

```bash
launchctl bootout gui/$UID/com.stockvis.celery-worker-neo4j 2>/dev/null || echo "이미 미로드(정상)"
launchctl bootout gui/$UID/com.stockvis.celery-watchdog     2>/dev/null || echo "이미 미로드(정상)"
```
> 12:35 측정 기준 두 잡은 **이미 미로드**. `bootout`은 no-op일 수 있음 — 정상.

### ② plist 교체

```bash
SRC=~/worktrees/sv-worker-runtime/scripts/ops/launchd   # 랜딩 후 경로
DST=~/Library/LaunchAgents
cp "$DST/com.stockvis.celery-worker-neo4j.plist" "$DST/com.stockvis.celery-worker-neo4j.plist.bak-20260831"
cp "$DST/com.stockvis.celery-watchdog.plist"     "$DST/com.stockvis.celery-watchdog.plist.bak-20260831"
cp "$SRC/com.stockvis.celery-worker-neo4j.plist.proposed" "$DST/com.stockvis.celery-worker-neo4j.plist"
cp "$SRC/com.stockvis.celery-watchdog.plist.proposed"     "$DST/com.stockvis.celery-watchdog.plist"
plutil -lint "$DST/com.stockvis.celery-worker-neo4j.plist" "$DST/com.stockvis.celery-watchdog.plist"
```

### ③ bootstrap + enable  ← **게이트 통과 후에만**

```bash
launchctl bootstrap gui/$UID "$DST/com.stockvis.celery-worker-neo4j.plist"
launchctl enable    gui/$UID/com.stockvis.celery-worker-neo4j
```

### ④ kickstart

```bash
launchctl kickstart -k gui/$UID/com.stockvis.celery-worker-neo4j
```

### ⑤ 검증

```bash
# 1) 로그 첫 줄에 트리 경로 확인 (Desktop이 보이면 즉시 ⑥ 롤백)
tail -40 ~/Library/Logs/stockvis/celery-worker-neo4j.log | grep -E "worktrees|Desktop"

# 2) 워커 ping
~/Library/Caches/pypoetry/virtualenvs/stock_javis_system-_jE0wOmK-py3.12/bin/celery \
  -A config inspect ping -d neo4j@$(hostname -s)

# 3) 실행 코드의 커밋 확인
launchctl print gui/$UID/com.stockvis.celery-worker-neo4j | grep -E "working directory|state|pid"
cd ~/worktrees/sv-worker-runtime && git rev-parse --short HEAD

# 4) 적체 큐 소진 + dirty 추세 10분 관찰
redis-cli -n 0 LLEN neo4j                       # 28 → 0 으로 감소해야 함
psql -d stock_vis -At -c "WITH v2f AS (SELECT DISTINCT source_document_id FROM sec_supply_chain_evidence WHERE prompt_version='v2') SELECT count(*) FROM sec_supply_chain_evidence e WHERE e.neo4j_dirty AND e.target_symbol_id IS NOT NULL AND NOT (e.prompt_version='v1' AND e.source_document_id IN (SELECT source_document_id FROM v2f));"
# 현재 0 — 기동 후에도 0 유지(증가 없음)이면 정상
```

**합격 기준**: 로그에 `worktrees/sv-worker-runtime` 노출 / `Desktop` 미노출 · ping 응답 · Redis `neo4j` 큐 28→0 · 실효 dirty 0 유지.

### ⑥ 되돌리기

```bash
launchctl bootout gui/$UID/com.stockvis.celery-worker-neo4j
cp "$DST/com.stockvis.celery-worker-neo4j.plist.bak-20260831" "$DST/com.stockvis.celery-worker-neo4j.plist"
# 재기동하지 않고 정지 유지 (§3 기준 데이터 손실 0)
```
> 스크립트 교정 롤백이 필요하면 main에서 `git revert <STEP 0 커밋>` 후 런타임 트리 재체크아웃.

---

## 5. 별도 절 — 결함 B: `celery-watchdog` (우선순위 2)

- **트리**: WorkingDirectory·스크립트·`PROJECT_DIR` 모두 Desktop. watchdog은 `.env`를 로드해 **Django `send_mail`을 Desktop 트리 코드로 실행**한다(쓰기는 아니나 구 설정·구 코드 경유).
- **관측된 증상**: 09:34 neo4j 워커 종료 이후 5분 주기로 `launchctl kickstart` 실패 → `Could not find service "com.stockvis.celery-worker-neo4j" in domain for user gui: 501` → **경보 메일 반복 발송**(08-31분 마지막 3회: 11:51, 12:01, 12:11). 누적 "재시작 실패" 로그 28건.
- **현재**: watchdog 자체도 미로드 → 경보 발송 중단됨. 동시에 **worker/beat 자동복구도 없는 상태**.
- **추가 결함(등재만, 이번 교정 범위 밖)**: watchdog 감시 대상에 **`com.stockvis.web`(daphne)가 없다** → API 다운 시 자동복구 불가. 08-31 12:12 실사고와 직결. → TASKQUEUE `RC-WATCHDOG-DAPHNE-COVERAGE` 후보.
- **집행**: §4 ①~③과 동일 절차(`com.stockvis.celery-watchdog`). 단 **neo4j 워커 ③ 완료·⑤ 합격 후에 watchdog을 올린다** — 순서가 뒤집히면 watchdog이 미교정 상태의 neo4j 워커를 kickstart 한다.

---

## 6. 별도 절 — 결함 C: `pg-backup` (우선순위 3, 읽기 전용)

- **트리**: Desktop. `pg_dump`만 수행하므로 **DB 쓰기 없음** → 오염 위험 없음.
- **실질 위험 — 실측 하향 정정(2026-08-31 RC-EXEC-TREE-LAND)**: `~/worktrees/sv-worker-runtime/.env`는 **`~/Desktop/stock_vis/.env`를 가리키는 심링크**(대상 실재 확인). 즉 두 트리가 **동일한 `.env` 실체를 공유**하므로 당초 우려한 "트리 간 `.env` drift → 엉뚱한 DB 백업"은 **현재 구성에서 발생 불가**. 결함 C의 교정 목적은 **위험 제거가 아니라 D-LAUNCHD-RUNTIME-TREE 규칙 일관성**(공유 편집 트리 의존 제거)이다.
- ⚠️ **잔여 의존**: 런타임 트리의 `.env`는 심링크이므로 **Desktop 본체 파일에 여전히 의존**한다. 본체 `.env`가 이동·삭제되면 런타임 3트리가 함께 깨진다(worker·api 모두 같은 심링크). 별건 등재 = `OPS-ENV-SYMLINK-DEPENDENCY`. (`sv-web-runtime`에는 `.env` 없음 — frontend는 별도 파일, pg-backup과 무관.)
- **현재**: 로드·정상(runs=39, last exit 0, 02:00 스케줄).
- **집행**: 서두를 필요 없음. STEP 0 스크립트 교정이 랜딩되면 plist만 `.proposed`로 교체 후 `bootout`→`bootstrap`. 다음 02:00 실행에서 로그 확인.

---

## 7. 별도 절 — 측정 중 관측된 런타임 사건 (조치 불요, 기록용)

측정 시작 시점(12:22~12:31) **stockvis 백엔드 잡 전면 정지** 관측: `celery-worker` / `celery-beat` / `celery-worker-neo4j` / `celery-watchdog` / `web`(daphne) / `verify-pair` 6건 미로드, celery·daphne 프로세스 0개, `127.0.0.1:18765` 무응답(curl exit 7). 살아있던 것은 `web-frontend`(:3000)와 Neo4j 엔진뿐.

**12:34:31에 `celery-worker`(81152) / `celery-beat`(81154) / `web`(81157) 3종이 launchd로 부트스트랩되어 복구됨** — 병진 측 조치로 판단. `celery-worker-neo4j`와 `celery-watchdog`은 **의도적으로 미로드 유지**(정지 유지 규율 준수). CC는 관여하지 않음.

---

## 8. 산출물

| 파일 | 내용 |
|------|------|
| `scripts/ops/launchd/com.stockvis.celery-worker-neo4j.plist.proposed` | 결함 A 교정 plist (lint OK) |
| `scripts/ops/launchd/com.stockvis.celery-watchdog.plist.proposed` | 결함 B 교정 plist (lint OK) |
| `scripts/ops/launchd/com.stockvis.pg-backup.plist.proposed` | 결함 C 교정 plist (lint OK) |
| `scripts/ops/launchd/exec-tree-selflocate.diff.proposed` | 래퍼 3건 `PROJECT_DIR` self-locate 교정 diff |
| `scratchpad/RC-NEO4J-WORKER-TREE_상신_20260831.md` | 본 문서 |
