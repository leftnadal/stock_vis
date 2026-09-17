# DSS-ASOF-1-R2 보고 — §2 착지 / §1 HALT 조건 재발 / §3 상신 완료

- 브랜치 `monorepo/sess-dss-asof` · worktree `~/worktrees/sv-dss-asof` · 커밋 **`72c4c896`**(선행 `5eaad521`)
- **prod DB 쓰기 0** · `--execute` 미실행 · `load_dss_week` 미실행 · 적재 경로 코드 무접촉 · launchd/`sv sync` 무접촉 · 브랜치/worktree 삭제 0
- 🔴 **main 머지·push 미집행** — 지시서 "§1·§2까지 게이트 통과 시 머지"에서 §1 미통과

---

## ① §0 — STEP 0-lite

| 항목 | 실측 |
|---|---|
| `origin/main` | **`bdadd045`** (직전 세션 `2eca515d` 대비 **+7**: SCB-RECOVER-PROBE·CS-RESUME-DEPLOY·DASH-TOP 랜딩) |
| `sess-dss-asof` | `5eaad521` · ahead 1 / **behind 7** · **clean** → **역머지 집행**(`02260cb3`, 충돌 0) |
| health (역머지 후 기준선) | **✅16 / ⚠1 / ❌1** — ❌`stale pending`(DUAL-OBS-1) · ⚠`실행 트리 뒤처짐`. **둘 다 기지 (i)형, 신규 (ii)형 0 → HALT 아님** |
| | (PROGRESS ❌는 타 세션 갱신으로 이미 해소됨) |
| 🔴 **`sv sync` 집행 여부** | **미집행.** `sv-worker/api/web-runtime` 3트리 전부 **`2eca515d`** = 09-15 09:13 재동기 상태 유지, `origin/main` 대비 **behind 7** |

> **야간 수치 해석 주의**: 3트리는 서로 정렬돼 있으나 origin/main보다 7커밋 뒤처진다. 09-15 09:13 이후 랜딩된 7커밋(DASH-TOP FE 포함)은 **라이브에 반영돼 있지 않다.** 09-16 야간 산출물은 그 기준으로 읽어야 한다.

---

## ② §1 — 동결 목록 확정 + 재전수검사

### 동결 목록 (코드 상수 = 단일 출처)
`packages/shared/market_week.py:ANCHOR_EXEMPTIONS` — 키 `(모델 레이블, 앵커)`, 값 = 근거 1줄.

| 모델 | 앵커 | 근거 |
|---|---|---|
| `SymbolDemandSignal` | 2026-07-24 | 2026-08-16 일괄백필 — 실행시각이 데이터 내용과 무관(소급 적재) |
| `SymbolDemandSignal` | 2026-07-31 | 〃 |
| `SymbolDemandSignal` | 2026-08-07 | 〃 |
| `EstimateSnapshot` | 2026-07-29 | 2026-07-29(수) 임시수집 — 주간 마감일이 아님(앵커 쪽이 주간 라벨이 아니다) |

09-11 항목은 지시서대로 **미리 넣지 않았다**(§3 집행 후 추가 — 단, 백필분은 `created_at`이 원본 유지라 **규칙을 지키므로 동결 자체가 불필요**하다).

### 🔴 재전수검사 — **위반 2건** (지시서 기대 0건 → HALT 조건 충족)

`scripts/asof_anchor_sweep.py` (read-only) 출력:

| 모델 | 앵커 | 관측시각(ET) | as_of | 판정 |
|---|---|---|---|---|
| EstimateSnapshot | 07-17·07-24·07-31·08-07·08-14·08-21·08-28·09-04 (8건) | — | — | **OK** |
| EstimateSnapshot | 2026-07-29 | 07-29 15:01 Wed | 07-24 | 동결(검증 제외) |
| **EstimateSnapshot** | **2026-09-12** | 09-12 15:03 Sat | 09-11 | **\*\*\* VIOLATION** |
| SymbolDemandSignal | 07-24·07-31·08-07 (3건) | 08-15 21:01 Sat | 08-14 | 동결(검증 제외) |
| SymbolDemandSignal | 08-14·08-21·08-28·09-04 (4건) | — | — | **OK** |
| **SymbolDemandSignal** | **2026-09-12** | 09-12 18:04 Sat | 09-11 | **\*\*\* VIOLATION** |

**총 위반 2건 — 둘 다 09-12.**

**근인**: `D-DSS-W11-RESCUE` §3-4가 *"09-12 앵커 행은 삭제하지 않는다"* 로 확정했으므로 두 행은 **영구 잔존**하고, 따라서 위반도 영구 잔존한다. 지시서가 제시한 **초기 동결 4건에 09-12가 빠져 있다.**

**CC 미조치 근거**: §1-3 원문 — *"동결 목록에 항목을 추가하는 것은 사람의 결정이지 테스트를 통과시키는 수단이 아니다."* 이 문장을 테스트 헤더에 박제해 놓고 같은 세션에서 09-12를 자기 추가하면 그 규율을 스스로 깬다. **상신만 한다.**

**선택지** (TASKQUEUE `DSS-ASOF-EXEMPT-0912`):
- ⒜ 09-12 2건을 동결 추가 — 근거는 이미 존재한다(본 사건의 드리프트 + §3-4 흔적 보존 결정)
- ⒝ sweep 범위를 "신규 앵커만"으로 축소
- ⒞ 09-12 행 삭제 (§3-4 결정 번복)

### 회귀 고정
`tests/unit/shared/test_anchor_contract.py` — 동결 목록이 정확히 4건인지 · 항목별 근거 존재 · **(모델, 앵커) 쌍 스코프**(날짜만으로 다른 모델까지 면제되지 않음) · 자동발화 8건 통과 · 백필 3건 스킵 + 같은 관측시각이라도 비동결 앵커는 잡힘 · **새 드리프트 앵커는 RED**.

---

## ③ §2 — 발화 계약 감시 **독립 착지** (as_of 의존 0)

### H-1 `주간 발화 계약` (health 검증 19)
- 판정: **직전 금요일(ET) 앵커의 DB 행 존재.** `as_of_week` **미사용** — 직전 금요일 산술을 인라인 중복 정의했다. *감시가 라벨 교정 로직에 의존하면 백필이 감시를 통과시킨다*(감시가 감시 대상에 의존하는 순환).
- `last_run_at` **미사용** (등재 원칙).
- 임계 **+48h WARN / +96h ERROR** — 하루 밀림은 catch-up으로 회복(09-12→09-13 실사례)이라 즉시 ERROR는 경보 피로.
- 🔑 **유효신호 0 조항**: `SymbolDemandSignal` 최신 앵커가 전건 `excluded`면 **ERROR**.

**라이브 점등 확인** — 실제로 09-12 조건을 잡는다:
```
❌ ERROR  주간 발화 계약  직전 금요일 2026-09-11 기준 —
          EstimateSnapshot 2026-09-12 ✓ / SymbolDemandSignal 유효신호 0
   └ SymbolDemandSignal: 앵커 2026-09-12 행 502건이나 excluded=False가 0건
     — 행은 있으나 신호 없음(전건 제외). prev 앵커 부재 의심
   └ 이 판정이 틀릴 수 있는 조건: 앵커 라벨이 실행일 기준이라 하루 밀린 발화도 '도착'으로
     읽는다(라벨 정확성은 asof_anchor_sweep이 별도로 본다) · 미국장 휴장으로 금요일
     미발화가 정상인 주는 구분하지 못한다
```
→ **사건 당시 3일간 아무도 보지 못한 blind spot이 이제 ERROR로 뜬다.**

### H-2 `서비스 재기동 폭풍` (health 검증 20) — **만들었다**
계수 소스를 STEP 0에서 **실측 확정**했다:

| 서비스 | 로그 | 기동 배너 | 전 기간 건수 |
|---|---|---|---|
| celery-beat | `celery-beat-error.log` | `beat: Starting...` | 3,410 (09-12 사건 3,276 포함) |
| celery-worker | `celery-worker-error.log` | `celery@<host> ready.` | 391 |
| celery-worker-neo4j | `celery-worker-neo4j-error.log` | `neo4j@<host> ready.` | 44 |
| web(daphne) | `web-error.log` | `Listening on TCP address` | 114 |
| ~~web-frontend~~ | — | **미확정** | **제외** |

임계 **>20 WARN / >200 ERROR**(정상 일 0~3회 vs 사건 3,276회 — 오탐 여지 없는 마진).
대용량 로그(384MB+) 전수 스캔을 피해 **꼬리 4MB만** 읽고, 과소 계수 조건을 경보 문구에 병기했다.
현재: `celery-beat 0 / celery-worker 0 / celery-worker-neo4j 1 / web(daphne) 0` → ✅ OK.

> web-frontend를 넣지 않은 이유 = 지시서 *"소스가 불명확하면 만들지 말고 보고"*. **측정 장치 오탐 원장 5건을 6건으로 늘리지 않는다.**

### DoD
| 항목 | 결과 |
|---|---|
| 기존 항목 **출력 문자열 diff 0** | ✅ (신규 2항목·시각·합계 줄만 제외하고 `diff` 무출력) |
| 역케이스 유닛 | **12 passed** — 정상 미점등 / 결번+16h(유예창) 미점등 / 결번+114h **점등** / **전건 missing_prev 점등** / 폭풍 300회 **점등** / 48h 밖 미계수 / 로그 부재 None / 직전금요일 산술 4케이스 |
| 경보 문구에 "틀릴 수 있는 조건" | ✅ 양쪽 모두 병기 |
| 머지 | 🔴 **보류** (§1 미통과) |

---

## ④ §3 — 09-11 백필 준비·상신 (집행 금지 준수)

### P1~P5 실측 (2026-09-16) — **전건 PASS**

| # | 확인 | 실측 | 판정 |
|---|---|---|---|
| **P1** | `EstimateSnapshot` anchor=2026-09-11 행수 | **0** | ✅ (0이 아니면 upsert 덮어쓰기 → HALT였다) |
| **P2** | `EstimateSnapshot` anchor=2026-09-12 | **1005행 / 503심볼** (FY2026·FY2027) | ✅ 기대 일치 |
| **P3** | `SymbolDemandSignal` anchor=2026-09-11 행수 | **0** | ✅ |
| **P4** | prev 조회 = `anchor − 7일` | `demand_signal.py:91` `prev = anchor - timedelta(days=WOW_LAG_DAYS)` · `WOW_LAG_DAYS = 7` · 폴백 없음 | ✅ 코드로 고정 |
| **P5** | 관측시각 필드 | `created_at` (`auto_now_add=True`) · 09-12 값 `19:03:12 ~ 19:13:26 UTC` | ✅ 있음 → 복제 시 원본 유지 구현 |

> P5 함정: `auto_now_add=True`라 `bulk_create`가 새 값을 박는다. 명령은 `bulk_create` 직후 `bulk_update(["created_at"])`로 되돌린다(bulk_update는 auto_now_add 미적용). **출처가 원장에 남는다.**

### dry-run 출력 (쓰기 0)
```
백필 2026-09-12 → 2026-09-11   (DRY-RUN)
  대상 행수 : 1005  / 심볼 503
  충돌      : 0  (0이어야 진행)
  관측시각  : 원본 유지 (created_at 2026-09-12 19:03:12.338728+00:00 ~ 2026-09-12 19:13:26.846819+00:00)
  샘플 3행 (before → after):
    A      FY2026  eps_avg=6.2022  2026-09-12 → 2026-09-11  (created_at 2026-09-12 19:03:12+0000 유지)
    A      FY2027  eps_avg=6.7447  2026-09-12 → 2026-09-11  (created_at 2026-09-12 19:03:12+0000 유지)
    AAPL   FY2026  eps_avg=8.8328  2026-09-12 → 2026-09-11  (created_at 2026-09-12 19:03:13+0000 유지)
  예상 소요 : bulk_create 1005행 + bulk_update(created_at) — 수 초
  dry-run — 쓰기 없음. 실집행은 --execute.
```

**가드 반증 실측** (안전장치 ①이 실제로 막는지 확인):
```
$ manage.py backfill_snapshot_anchor --from 2026-09-12 --to 2026-09-04
CommandError: 거부: 대상 앵커 2026-09-04에 이미 1004행이 있다.
              EstimateSnapshot은 upsert 모델이라 덮어쓰기 위험 — 수동 확인 필요.
```

### 집행 B 사후검증 **예측** (CC 독립 산출, read-only 시뮬레이션)

| 검증 | 예측 | 임계 |
|---|---|---|
| `missing_prev` | **0** | 0 아니면 중단 |
| 유효분모 | **487** (n=502 − excluded 15) | — |
| excluded 내역 | `analyst_delta` 14 · `fy_mismatch` 1 | — |
| up / down / flat | **149 / 138 / 200** | — |
| **`flat_ratio`** | **41.07%** | 클린 임계 90% → **통과** · 60% 초과면 보고(해당 없음) |

지시서 사전계산 ≈40.3% 대비 **+0.77%p** — 근사 일치.
**클린 WoW 쌍 4 → 5** 예상(09-11 종단 쌍 편입). 6/6 성숙은 09-18 회차에 달림.

**상신 문서**: `scratchpad/DSS-W11-BACKFILL_상신_20260915.md` — 집행 A(기한 09-19 05:30 KST 전, 사후검증 3개 = 행수 1005·심볼 503·값 해시 IDENTICAL) · 집행 B(🔴 A 없이 B 금지) · 되돌리기(삭제 대상·조건 4) · 09-12 행 보존 · **09-19 이중 게이트 경고**(05:30 스냅샷 / 07:00 C8 / 08:00 DSS / 09:00 RC-A-1 ⑧ — 전부 머신 가동+**콘솔 로그인** 필요, 09-12 `device_absent` 전례) · 09-18 beat 생존 1줄.

---

## ⑤ §4 — `DSS-ASOF-2` 재료 (구현 금지 준수)

- **앵커 결정 지점 = 2곳뿐**
  - `apps/chain_sight/tasks/estimate_tasks.py:40` `snapshot_date = timezone.now().date()`
  - `apps/chain_sight/tasks/dss_tasks.py:34` `et_today = timezone.now().astimezone(ET).date()`
- **제약/인덱스**: `EstimateSnapshot` `unique_together (symbol, snapshot_date, fiscal_year)` · `SymbolDemandSignal` `unique_together (symbol, anchor_date)` + `dss_signal_anchor_idx`. 앵커 **값 의미만** 바뀌므로 **마이그레이션 불요**.
- **가드 diff 규모**: `dss_tasks.py:42` `if latest != et_today` → as_of 기반 전환 시 1줄. 09-12형 skip이 소멸한다.
- **행위보존 증명 방법**: 자동발화 12건(동결 4건 제외한 sweep 모집단)에 신·구 로직을 모두 적용해 **동일 앵커 산출**을 보인다. 모집단은 `scripts/asof_anchor_sweep.py`가 이미 출력하므로 신규 계측 불요.
- ⚠️ **부수 발견(동반 수리 권고)**: `estimate_tasks.py:40`의 `timezone.now().date()`는 `USE_TZ=True`에서 **UTC 날짜**다. 20:00 ET 이후 실행되면 하루 앞선 날짜가 박힌다. 현재까지 실해 0(최근 실행 전부 20:00 ET 이전)이나 as_of 전환 시 함께 고친다.

---

## ⑥ 지시서 가정과 달랐던 점

1. 🔴 **§1-2 "불일치 0건" 미달 — 위반 2건(09-12).** 초기 동결 4건에 09-12가 누락됐고, §3-4의 "09-12 행 보존" 결정 때문에 **영구 잔존**한다. §1-3 규율상 자기 추가 불가 → 상신.
2. 🔴 **처분 문서 부재** — `claude/처분_DSS-ASOF-1_HALT해제_4결정_20260915.md` 디스크 전무(`claude/`에는 8월 지시서 4건뿐). 지시서 본문의 결정 요약으로 갈음했다. **병진 위임 문구도 대화에 없어 `--execute` 미실행.**
3. **`origin/main`이 +7 전진** — 지시서는 `5eaad521`에서 바로 이어가는 것을 전제했으나 역머지가 선행돼야 했다(충돌 0).
4. **`sv sync` 미집행** — 런타임 3트리가 origin/main보다 behind 7. 09-15 09:13 이후 랜딩분은 라이브 미반영.
5. **PROGRESS 방치 시각** — 지시서 "96.8h·12커밋"이었으나 타 세션이 이미 갱신해 실측 **21.8h**이고 health ❌에서 빠져 있었다(❌는 `stale pending` 1건뿐).
6. **H-2를 만들 수 있었다** — 계수 소스 4/5 실측 확정(web-frontend만 미확정). 지시서는 "불명확하면 만들지 말라"였고, 4종이 확정됐으므로 그 범위로 만들고 미커버를 경보 문구에 명기했다.
7. **09-11 백필분은 동결이 불필요하다** — `created_at`을 원본(09-12 19:03 UTC = 15:03 ET 토)으로 유지하므로 `as_of_week` = 09-11 = 앵커로 **규칙을 지킨다.** 지시서 1-1의 "(§3 집행 후) 2026-09-11 추가" 예정 항목은 실제로는 추가할 필요가 없다.
8. **`EstimateSnapshot`이 append-only가 아니다** — `update_or_create` upsert(직전 세션 발견). 백필 명령의 "대상 앵커 비어있지 않으면 거부" 가드의 근거이며, 별건 `DSS-LEDGER-IMMUTABLE`로 최우선 등재했다.

---

## 게이트 요약

| 게이트 | 결과 |
|---|---|
| pytest `tests/unit/shared` + `tests/ops` | **130 passed** |
| pytest + health_check 기존 3파일 | **147 passed** |
| ruff (신규·수정 파일) | **0** (선존 `health_check.py:810 F541` 1건은 범위 밖 유지) |
| health 기존 항목 출력 diff | **0** |
| health 합계 | ✅17 / ⚠1 / ❌2 (신규 ERROR = 09-12 유효신호 0 = **진짜 조건**) |
| 커밋 | `72c4c896` (브랜치 전용) |
| **머지·push** | 🔴 **미집행** — §1 미통과 |
