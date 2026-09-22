# DSS-ASOF-1-R2 애든덤 보고 — HALT 해제 · 착지 완료 · 백필 집행 완료

- 브랜치 `monorepo/sess-dss-asof` · worktree `~/worktrees/sv-dss-asof`
- **착지: `origin/main` = `79ed64fa`** (no-ff 머지 `b85db3ed` 계열, 세션 브랜치 조상 확증 ✅)
- 위임 범위 밖 prod 쓰기 0 · 되돌리기 미실행 · `sv sync`/launchd/서비스 재기동 무접촉 · 브랜치/worktree 삭제 0

---

## ① 동결 구조 변경 + 재전수검사 → **위반 0건**

`ANCHOR_EXEMPTIONS`를 평평한 목록 → **`{(모델, 앵커) → (사유코드, 근거)}`** 로 전환하고 사유코드 3종을 신설했다.

| 사유코드 | 대상 | 근거 |
|---|---|---|
| `MANUAL_BACKFILL` | SymbolDemandSignal 07-24·07-31·08-07 | 2026-08-16 일괄백필 — 사람이 만든 소급 적재 |
| `MANUAL_ADHOC` | EstimateSnapshot 07-29 | 수요일 임시 관측 — 주간 마감일이 아님 |
| `INCIDENT_PRESERVED` | EstimateSnapshot·SymbolDemandSignal **09-12** | celery-beat 크래시루프(09-12 02:23~12:31 KST)로 09-11 발화 소실·관측 1일 지연 기록. 사건 흔적 보존(디렉터 결정) |

**`scripts/asof_anchor_sweep.py` → 총 위반 `0건`.** (EstimateSnapshot 8 OK + 동결 2 / SymbolDemandSignal 4 OK + 동결 4)

### 쓰레기통화 방지 장치 (§2-3)
`tests/unit/shared/test_anchor_contract.py` 헤더 주석:
> 🔴 **동결 항목은 사유코드를 갖는다. 사유코드 없이 추가할 수 없고, 새 사유코드를 만드는 것은 디렉터 결정이다.**

테스트가 RED로 잡는 것: 사유코드 누락·미등록 코드·`INCIDENT_PRESERVED`의 09-12 외 확대·새 드리프트 앵커.
**09-11은 비동결**로 박제(`test_2026_09_11_backfill_is_not_exempt`) — 백필분은 `created_at` 원본 유지라 규칙을 지킨다.

---

## ② 머지 · push

| | 값 |
|---|---|
| 세션 커밋 | `054fbb5a` (애든덤 집행) · 선행 `72c4c896`·`e34e350a`·`5eaad521` |
| 착지 머지 | `b85db3ed` (no-ff, 임시 브랜치 `land-dss-asof-84251` 경유) |
| **최종 `origin/main`** | **`79ed64fa`** |
| 본진 트리 | **무접촉** — 타 세션이 `monorepo/sess-near-stop` 체크아웃 중이라 내 worktree의 임시 브랜치에서 `HEAD:main` push |

**역머지 4회** — 발부 시점 `0ff0949e` → 게이트 중 `329716b4` → push 거부(+15) → 최종 흡수. 세션 내내 origin/main이 고회전했다(총 +23 흡수, **충돌 0**).
착지 트리 게이트(LAND는 대상 트리에서 측정): pytest **138 passed** · sweep **위반 0** · health **✅19/⚠2/❌0**.

---

## ③ DST 판정 — **⑵ (ET 변환) · 🟢 폭탄 없음**

**코드 좌표**: `apps/chain_sight/tasks/dss_tasks.py:34`
```python
et_today = timezone.now().astimezone(ET).date()      # ET = ZoneInfo("America/New_York")
```

| | ET | UTC | `.date()` 결과 |
|---|---|---|---|
| EDT 금 19:00 (현재) | 2026-09-18 19:00 | 2026-09-18 23:00 금 | **09-18 금** |
| **EST 금 19:00** (11-01 이후) | 2026-11-06 19:00 | **2026-11-07 00:00 토** | **11-06 금** ✅ |

애든덤 표의 "🔴 00:00 UTC 토 → 앵커 토요일 → 11-06 확정 재발"은 **DSS가 UTC 날짜를 쓴다는 전제** 위에 있었다. 코드는 `astimezone(ET)`를 거치므로 UTC가 토요일로 넘어가도 **ET 기준 날짜는 금요일을 유지**한다. → **`DSS-ASOF-2`에 11-06 기한 불요.**

### ⚠️ 잔존 위험 (스냅샷 쪽 · 다른 종류)
`apps/chain_sight/tasks/estimate_tasks.py:40`
```python
snapshot_date = timezone.now().date()                 # ← UTC 날짜
```
- 정시 16:30 ET: EDT 20:30 UTC · EST 21:30 UTC → **둘 다 금요일** (안전)
- **catch-up 지연 발화**가 **20:00 ET(EDT) / 19:00 ET(EST)** 를 넘기면 UTC 날짜가 토요일로 넘어가 **앵커가 토요일로 박힌다.**
- 09-12 catch-up은 15:03 ET였으므로 약 5시간 여유로 안전했다. **우연이었다.**

**수정 0** — 지시서대로 읽기만 했다. `DSS-ASOF-2` 동반 수리 대상으로 TASKQUEUE 등재.

---

## ④ 백필 집행 — A·B 검증 **6종(+1) 전건 PASS**

### 0단계 선행 재확인 (캐리오버 금지)
| 확인 | 실측 | 판정 |
|---|---|---|
| `EstimateSnapshot` anchor 09-11 | **0** | ✅ (0 아니면 즉시 중단이었다) |
| `SymbolDemandSignal` anchor 09-11 | **0** | ✅ |
| `EstimateSnapshot` anchor 09-12 | **1005행 / 503심볼** | ✅ |

### 집행 A — `backfill_snapshot_anchor --from 2026-09-12 --to 2026-09-11 --execute`
```
완료: 2026-09-11 앵커 1005행 INSERT (원본 1005행)
```
| # | 검증 | 실측 | 판정 |
|---|---|---|---|
| ① | 행수 | **1005** | PASS |
| ② | 심볼 | **503** | PASS |
| ③ | 값 해시(7필드 정렬 SHA256) | `45d825ef5232a866` **= 09-12와 IDENTICAL** | PASS |
| ④ | `created_at` 원본 유지 | `2026-09-12 19:03:12 UTC` = **ET 09-12 15:03 Sat** (표본 3행) · 범위 `19:03:12 ~ 19:13:26 UTC` | PASS — `auto_now_add` 덮어쓰기 **미발생** |

### 집행 B — `load_dss_week --anchor 2026-09-11`
```
anchor=2026-09-11 written_signals=502 written_scores=11 skipped_existing=False
  n=502 up=149 down=138 flat=200 excl=15
  invariant: 합=n True · breadth∈[-1,1] True · 유효분모>0 True · Score=11
  flat_ratio=41.07% (정상 <60)
```
| # | 검증 | 예측 | 실측 | 판정 |
|---|---|---|---|---|
| ① | `missing_prev` | 0 | **0** | PASS |
| ② | 유효분모 | ≈487 | **487** | PASS |
| ③ | `flat_ratio` | 41.07% | **41.07%** | PASS (임계 90% · 중단선 60%) |

exclude 내역 = `analyst_delta` 14 · `fy_mismatch` 1. `ThemeDemandScore` date=09-11 **11행**.
**예측과 실측이 소수점까지 일치** — 시뮬레이션이 정확했다.

### 클린 WoW 쌍 **4 → 5** ✅
`07-31 · 08-07 · 08-28 · 09-04 · **09-11**` (양끝 비축퇴 · flat_ratio < 90%)
제외: 07-24(prev 07-17 판정부재) · 08-14(self 축퇴) · 08-21(prev 축퇴) · 09-12(유효분모 0)
**6/6 성숙은 09-18 회차 클린 여부에 달린다.**

---

## ⑤ 추가 수리 — H-1 영구 고착 오탐 (계획 밖 · 필요했다)

백필 후 health가 계속 `❌ SymbolDemandSignal 유효신호 0`을 냈다. H-1이 **최신 앵커 하나(09-12)** 만 보기 때문이다. 09-11에 유효신호 487건이 생겼는데도 09-12(유효 0)가 보존 결정으로 영구 잔존하므로 **이 ERROR는 영원히 꺼지지 않는다.**

**수리**: 판정 범위를 최신 1건 → **직전 금요일 이후 앵커 전체**로 확대. 그중 하나라도 유효하면 그 주의 발화는 성립한 것으로 본다.

```
✅ OK  주간 발화 계약  직전 금요일 2026-09-11 기준 —
       EstimateSnapshot 2026-09-12 ✓ / SymbolDemandSignal 2026-09-12 ✓(유효 487/1004)
```

**검출력 보존 확인**: 그 주 앵커 전체가 유효 0이면 여전히 ERROR(역케이스 유지). 역케이스 **+1**(`test_drifted_week_with_one_usable_anchor_does_not_fire`) → 총 13건.

> 꺼지지 않는 경보는 경보가 아니다. 오탐을 없애려다 실장애를 놓치면 개악이지만, 영구 고착 경보는 그 자체로 감시를 무력화한다.

---

## ⑥ 기록 요지

- **DECISIONS +3**: `D-ASOF-EXEMPT-0912`(가중합 4.88·마진 1.45·사유 분류) · `D-DSS-W11-RESCUE 집행 위임`(**위임 문구 원문 인용** + 범위 한정 + 집행 결과) · `D-LLM-CREDIT-CLOSE`.
- **common-bugs 채번 후보 +1**: *"지시서의 두 조항이 같은 대상을 다르게 규정하면 실행자는 반드시 멈춘다"* — 발부 전 DoD 달성가능성 1회 검산 + 실행 측은 자가 해소 대신 모순 두 조항 인용 상신.
- **TASKQUEUE**: `DSS-ASOF-EXEMPT-0912` **종결** · `DSS-ASOF-2` DST 판정 반영(11-06 기한 불요 + 스냅샷 catch-up 잔존 위험) · **`OPS-LAUNCHD-DAEMON-1` 신규**(user agent라 재부팅 후 콘솔 미로그인 시 전 스택 정지 — 09-12 6h05m 실측 · **이번 주 착수 금지**) · `OPS-LOG-FLOOD` 악화 실측(**약 1.3GB**) · `DSS-LEDGER-IMMUTABLE` 유지 · **`LLM-CREDIT-OUTAGE` → ✅ SUPERSEDED** · **`NEWS-ANALYSIS-SELECTION` 등재**(소유 = 도메인 트랙, ops는 등재만·설계 안 함).
- **PROGRESS**: 세션 요지 + **DUAL-OBS-1 해소 델타 부기** → health `stale pending` ❌ **해소**(❌2 → **❌0**).

---

## ⑦ 지시서 가정과 달랐던 점

1. **DST 폭탄이 없었다.** 애든덤 표는 DSS가 UTC 날짜를 쓴다고 전제했으나 `dss_tasks.py:34`는 `astimezone(ET)`를 거친다. 판정 ⑵. 위험은 오히려 **스냅샷 쪽의 catch-up 지연**이라는 다른 형태로 존재한다.
2. **H-1에 계획에 없던 수리가 필요했다.** 백필이 성공하자 09-11(유효 487)과 09-12(유효 0)가 같은 주에 공존하게 됐고, 최신 앵커만 보는 H-1이 영구 고착 ERROR를 냈다. 백필 없이는 드러나지 않았을 결함이다.
3. **`origin/main`이 세션 중 +23 전진**(`0ff0949e` → `329716b4` → … → `79ed64fa`), **역머지 4회**. 앵커 갱신이 경고한 "세 번째"를 넘겼다. 매 흡수 충돌 0. push가 한 번 거부(behind 15)됐고, 흡수→게이트→push를 한 호출로 묶어 해소했다.
4. **본진 트리를 쓸 수 없었다** — 타 세션이 `monorepo/sess-near-stop`으로 체크아웃 중이라 임시 브랜치 경유로 착지했다(선례 `land-recover-1`과 동형).
5. **health ❌가 2건 → 0건**이 됐다. `stale pending`(DUAL-OBS-1)은 §6 부기가 PROGRESS의 ⏸️ 블록까지 닿아야 해소되는 구조였다(TASKQUEUE 상태 전환만으로는 안 꺼진다).
6. **본진 트리에 타 세션 산출물 `$OUT`**(6,772B, 09-15 12:38, IONQ 종목 출력)이 미추적으로 남아 있다. 내 것이 아니라 건드리지 않았다 — 소유 세션 확인 필요.
7. `scripts/health_check.py`가 타 세션 변경(+51줄, `check_story_title_gate`)과 자동병합됐다. `CHECKS` 21항목·AST 정합 확인 완료.

---

## 남은 것

| 항목 | 상태 |
|---|---|
| **09-18(금) 19:00 ET 발화** | 백필 완료 후 **DSS·스냅샷 무접촉 유지 중**. beat 생존 1줄 절차는 상신 문서에 있음 |
| **09-19(토) 이중 게이트** | 05:30 스냅샷 · 07:00 C8(as_of=09-18) · 08:00 DSS · 09:00 RC-A-1 ⑧ — **전부 머신 가동 + 콘솔 로그인 필요** |
| 6/6 성숙 | 09-18 회차가 클린이면 달성 |
| 되돌리기 | 미실행(병진 수동) — 조건 미발생 |
