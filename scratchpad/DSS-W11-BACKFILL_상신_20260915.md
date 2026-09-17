# 상신 — 09-11 앵커 백필 집행 (DSS-W11-RESCUE)

> **CC는 dry-run까지 수행했다. 실집행은 병진 몫.** 이 대화에 명시 위임 문구가 없어 `--execute` 미실행.
> 근거 = `D-DSS-W11-RESCUE`(병진 ⓐ 채택 · 디렉터 추천 ⓑ) · G-2 증거 게이트 PASS(DSS-ASOF-1).
> 작성 2026-09-16 · 브랜치 `monorepo/sess-dss-asof`

## 전제 확인 (2026-09-16 실측 · 전건 PASS)

| # | 확인 | 실측 | 판정 |
|---|---|---|---|
| P1 | `EstimateSnapshot` anchor=2026-09-11 행수 | **0** | ✅ 덮어쓰기 위험 없음 |
| P2 | `EstimateSnapshot` anchor=2026-09-12 | **1005행 / 503심볼** (FY2026·FY2027) | ✅ 기대 일치 |
| P3 | `SymbolDemandSignal` anchor=2026-09-11 행수 | **0** | ✅ |
| P4 | prev 조회 = `anchor − 7일` 정확일자 | `demand_signal.py:91` `prev = anchor - timedelta(days=WOW_LAG_DAYS)`, `WOW_LAG_DAYS = 7` | ✅ 코드로 고정 |
| P5 | 관측시각 필드 | `created_at` (`auto_now_add=True`) · 09-12 값 `19:03:12 ~ 19:13:26 UTC` | ✅ 복제 시 원본 유지하도록 명령에 구현 |

> ⚠️ P5 주의: `auto_now_add=True`라 `bulk_create`가 새 값을 박는다. 명령은 `bulk_create` 직후
> `bulk_update(["created_at"])`로 원본 값을 되돌린다(bulk_update는 auto_now_add 미적용).
> **출처가 원장에 남는다** — 09-11 행의 관측시각이 09-12로 남아 백필분임이 드러난다.

---

## 집행 A — 앵커 복제  🕐 기한 **2026-09-19 05:30 KST 전** (= 09-18 16:30 ET 스냅샷 발화 전)

```bash
cd ~/worktrees/sv-dss-asof   # 또는 랜딩 후 메인 트리
~/Library/Caches/pypoetry/virtualenvs/stock_javis_system-_jE0wOmK-py3.12/bin/python \
  manage.py backfill_snapshot_anchor --from 2026-09-12 --to 2026-09-11 --execute
```

**dry-run 실측 출력 (2026-09-16, 쓰기 0)**
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
```

**가드 반증 실측** — 대상 앵커에 행이 있으면 거부한다:
```
$ manage.py backfill_snapshot_anchor --from 2026-09-12 --to 2026-09-04
CommandError: 거부: 대상 앵커 2026-09-04에 이미 1004행이 있다.
              EstimateSnapshot은 upsert 모델이라 덮어쓰기 위험 — 수동 확인 필요.
```

### 사후 검증 3개 (전부 충족해야 B로 진행)
```bash
manage.py shell -c "
from apps.chain_sight.models.heat import EstimateSnapshot as E
import datetime as dt, hashlib, json
q11 = E.objects.filter(snapshot_date=dt.date(2026,9,11))
q12 = E.objects.filter(snapshot_date=dt.date(2026,9,12))
print('① 행수 :', q11.count(), '(기대 1005)')
print('② 심볼 :', q11.values(\"symbol\").distinct().count(), '(기대 503)')
F=('symbol','fiscal_year','eps_avg','eps_high','eps_low','num_analysts_eps','revenue_avg')
h=lambda q: hashlib.sha256(json.dumps(sorted(map(str,q.values_list(*F))),ensure_ascii=False).encode()).hexdigest()[:16]
a,b=h(q11),h(q12); print('③ 값해시:', a, 'vs', b, '→', 'IDENTICAL ✅' if a==b else '*** 불일치 — 되돌리기')
"
```

---

## 집행 B — DSS 재적재  🕐 기한 09-19 판정 전 · 🔴 **A 없이 B 단독 실행 금지**

> 2026-09-14의 "무효·유해" 판정은 *09-11 스냅샷 0행* 전제 위에 있었다. A가 그 전제를 해소한 뒤에만 유효하다.

```bash
manage.py load_dss_week --anchor 2026-09-11
```

### 사후 검증 (CC 시뮬레이션 예측값 — read-only 산출, 2026-09-16)

| 검증 | 예측 | 임계 |
|---|---|---|
| `missing_prev` | **0** | 🔴 0이 아니면 즉시 중단 |
| 유효 신호(유효분모) | **487** (n=502 − excluded 15) | ~502 근방 |
| excluded 내역 | `analyst_delta` 14 · `fy_mismatch` 1 | — |
| up / down / flat | **149 / 138 / 200** | — |
| **`flat_ratio`** | **41.07%** | 클린 임계 90% → **통과 예상** · **실측이 60% 초과면 보고** |

> 지시서 사전계산 ≈40.3% 대비 **+0.77%p** — 근사 일치(CC 독립 산출).
> 시뮬레이션 방법: `_load_fy_rows(2026-09-12, FY2027)`를 백필 후 09-11 값의 대리로 삼고
> `prev = 2026-09-04`로 `classify_symbol` 전수 적용. 쓰기 0.

**클린 WoW 쌍 영향**: 09-11 종단 쌍이 `flat_ratio 41.07% < 90%` 및 prev(09-04) 비축퇴로 **클린 편입** →
클린 쌍 4 → **5**. 6/6 성숙은 09-18 회차 클린 여부에 달린다.

---

## 되돌리기 (파괴적 — 병진 수동 전용)

```bash
# ⚠️ 삭제 전 행수 확인 필수. 09-12 앵커는 건드리지 않는다.
manage.py shell -c "
from apps.chain_sight.models.heat import EstimateSnapshot as E, SymbolDemandSignal as S, ThemeDemandScore as T
import datetime as dt; d=dt.date(2026,9,11)
print('삭제 대상:', E.objects.filter(snapshot_date=d).count(), 'E /',
      S.objects.filter(anchor_date=d).count(), 'S /', T.objects.filter(date=d).count(), 'T')
# 확인 후: E.objects.filter(snapshot_date=d).delete(); S.objects.filter(anchor_date=d).delete(); T.objects.filter(date=d).delete()
"
```
**삭제 대상**: anchor 2026-09-11의 `EstimateSnapshot` 1005행 + `SymbolDemandSignal` ~502행 + `ThemeDemandScore` 11행.

**되돌릴 조건** (하나라도 해당 시):
1. 집행 A 사후검증 ③ **값 해시 불일치**
2. 집행 B `flat_ratio` 이상 — 60% 초과 또는 90% 이상(축퇴)
3. `missing_prev` ≠ 0
4. G-2 반증 정황 — 09-11 앵커의 개정 폭이 클린 7일 pooled 분포에서 벗어남

## 🔴 09-12 앵커 행은 삭제하지 않는다
유효신호 0이라 무해하고, 남아야 사건의 흔적이 원장에 남는다.
(부작용: `asof_anchor_sweep` 위반 2건이 영구 잔존 → **§1 동결 목록 안건** 참조.)

---

## 09-19(토) 아침 이중 게이트 ⚠️ 경고

| 시각(KST) | 게이트 | 필요 조건 |
|---|---|---|
| 05:30 | 09-18(금) 16:30 ET EstimateSnapshot 발화 | **머신 가동 + 콘솔 로그인** |
| 07:00 | heat beat → **C8 수렴 게이트**(as_of=09-18, −56=07-24 ✓) | 동일 |
| 08:00 | 09-18 DSS 판정 | 동일 |
| 09:00 | RC-A-1 ⑧ 감쇠 봉인 | 동일 |

🔴 **전례**: 2026-09-12에 Claude 데스크톱 예약이 `device_absent`로 미발화했고, 같은 날 머신이
12:31 종료 → 12:32 재부팅 → **18:37에야 콘솔 로그인**되어 그 6시간 5분 동안 전 스택이 정지했다.
`~/Library/LaunchAgents/com.stockvis.*`는 **user agent**(`LimitLoadToSessionType` 부재 = Aqua)라
**로그인 없이는 뜨지 않는다.** 09-19 새벽에 머신이 켜져 있고 로그인 상태여야 한다.

## 09-18(금) 오전 beat 생존 확인 (1줄)
```bash
launchctl list | grep stockvis.celery-beat && \
  tail -3 ~/Library/Logs/stockvis/celery-beat-error.log | cut -c1-90
```
→ PID가 있고 마지막 줄 타임스탬프가 수 분 이내면 생존. (재기동 폭풍은 새 health 항목
`서비스 재기동 폭풍`이 24h 창으로 감시한다 — 임계 >20 WARN / >200 ERROR.)
