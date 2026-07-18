# PROD_RUNBOOK_COACH_STACK — Coach 스택 통합 적용 (19b+19c+20a+sv sync)

> 실행자: 병진(수동). 형태: 원세션·게이트 내장(결정 2026-07-17, 옵션 ③).
> **절대 규칙: 게이트 실패 = 즉시 정지, 이후 단계 진행 금지, 게이트 출력 그대로 디렉터에 보고.**
> 게이트를 건너뛴 적용은 이 런북의 실행으로 인정되지 않는다.
>
> **실행 컨텍스트(실측):** prod DB 대상 명령(migrate·backfill·beat 등록·수동 킥)은 전부
> **prod 런타임 트리 `/Users/byeongjinjeong/worktrees/sv-worker-runtime`** 에서 실행한다
> (이 트리의 `.env` 가 prod DB를 가리킴 — 편집용 공유 트리에서 실행 금지). venv 활성 후
> `export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES PGGSSENCMODE=disable`(macOS fork, #25).
> `DJANGO_SETTINGS_MODULE=config.settings`(기본) — prod 여부는 트리의 `.env` 로만 갈린다.
>
> 사전 조건: prod DB 백업(또는 스냅샷) 확인 — **하우스 백업 = `scripts/pg-backup.sh`**
> (운영 스케줄 02:00). 최근 스냅샷 존재를 확인하거나 실행 직전 1회 수동 백업 후 진행.
> 실행 시각 권장: **beat 발화(19:00/19:15 ET) 전 저녁** — 등록과 첫 자동 발화 사이 간격 확보.
>
> **이 런북이 커버하는 스택(실측):**
> - **19b**: FX·KRW numéraire — fx 앱 `0001_initial` + portfolio `0004_walletholding_acquisition_fx_rate` + `backfill_fx_rates`
> - **19c**: 배치 엔진 v2 — portfolio `0005_usergoal_aggressiveness_offset_and_more`(손잡이 5종 + 원장 2종 PortfolioSnapshot·AdvisoryRun 생성) + snapshot beat
> - **20a**: 권유 읽기 — portfolio `0006_advisoryrun_trigger` + advisory beat
> - **20b**: REST + 화면(마이그레이션 0) — sv sync 로만 런타임 반영
>
> ※ **마이그레이션 실명 = coach-stack 4개**(fx 0001 · portfolio 0004·0005·0006). portfolio
> `0002`(18-R UserGoal/CashBalance)·`0003`(19a 다통화)는 선행 슬라이스 소관이나, prod 가
> 그보다 뒤에 있으면 `migrate` 가 연속 체인으로 함께 적용한다(전부 additive). 그래서 **S1 은
> 개수를 못 박지 않고 `showmigrations`(적용 전 pending 확인) → `migrate` → `showmigrations`
> (unapplied 0) 로 게이트한다.**

---

## S1. 마이그레이션 (스키마 가산 — coach-stack)

```bash
cd /Users/byeongjinjeong/worktrees/sv-worker-runtime
source <venv>/bin/activate   # 이 트리의 venv
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES PGGSSENCMODE=disable

# 적용 전 pending 확인 (기대: fx 0001 [ ], portfolio 0004·0005·0006 [ ] 미적용;
#  prod 가 더 뒤면 0002·0003 도 [ ] 로 보일 수 있음 — 전부 additive)
python manage.py showmigrations fx portfolio

python manage.py migrate
```

### G1 게이트 — 통과해야 S2
- `python manage.py showmigrations fx portfolio` → coach-stack 전부 `[X]`:
  - `fx  [X] 0001_initial`
  - `portfolio  [X] 0004_walletholding_acquisition_fx_rate`
  - `portfolio  [X] 0005_usergoal_aggressiveness_offset_and_more`
  - `portfolio  [X] 0006_advisoryrun_trigger`
  - **fx·portfolio 에 `[ ]`(미적용) 잔여 0**
- 기존 화면 로드 스모크: 대시보드 GET `curl -s -o /dev/null -w "%{http_code}" https://<prod-host>/api/v1/dashboard/eod/latest/` → **200**
  (또는 이미 서빙 중인 아무 GET 화면 1개 — 마이그레이션이 기존 서빙을 깨지 않았는지 확인)
- 실패 시: 정지. `migrate` 출력 전체 + `showmigrations fx portfolio` 출력 보고.

## S2. backfill_fx_rates (유일한 데이터 쓰기 단계)

```bash
# 같은 sv-worker-runtime 트리에서
python manage.py backfill_fx_rates            # --pair 기본 USDKRW
# 출력 예: "FX backfill USDKRW: fetched=NNNN created=NNNN updated=NNNN"
```
멱등성: **재실행 안전**(`ExchangeRate.update_or_create(pair, date)` — 재실행 시 created=0/updated=N).
인자: `--pair`(기본 `USDKRW`) 하나뿐. 기간 옵션 없음 — FMP 래퍼가 반환하는 전체 히스토리를 백필.

### G2 게이트 (핵심) — 통과해야 S3
prod `manage.py shell` 에서(같은 트리):
```python
from packages.shared.fx.models import ExchangeRate
from django.db.models import Min, Max
qs = ExchangeRate.objects.filter(pair="USDKRW")
print("count=", qs.count())
print(qs.aggregate(Min("date"), Max("date")))
r = qs.order_by("-date").first()
print("latest=", r.date, r.close)
```
- 행수: `count` → **≥ 1,300** (약 5년치 영업일; dev 실측 기준 1,373 — 최소 1,300 이상)
- 커버리지: `date__min` ≈ 5년 전, `date__max` = 최근 영업일(주말·공휴일 제외 며칠 이내)
- 표본 정합: `latest close` → **USD/KRW 상식 범위 1,000 ~ 2,000** (dev 실측 최근 close 1,491.09)
- 실패/부분 실패 시: 정지. **beat 미등록 상태 유지**(오염 권유 생성 차단). 위 쿼리 출력 보고.

## S3. beat 2종 등록 + 수동 킥

```bash
# 같은 sv-worker-runtime 트리에서. 멱등(update_or_create, #28 DatabaseScheduler).
python manage.py sync_portfolio_snapshot_beat     # portfolio-snapshot-daily @ 19:00 ET
python manage.py sync_portfolio_advisory_beat      # portfolio-advisory-daily @ 19:15 ET
# (등록 전 예정만 보려면 각 커맨드에 --dry-run)
```
등록 대상(실측):
- `portfolio-snapshot-daily` → `apps.portfolio.tasks.snapshot_all_users` · crontab **19:00 America/New_York, dow=1-5**
- `portfolio-advisory-daily` → `apps.portfolio.tasks.advisory_all_users` · crontab **19:15 America/New_York, dow=1-5**

수동 킥(즉시 1회 — 하우스 방식 = shell `.apply()` 동기):
```python
from apps.portfolio.tasks import snapshot_all_users, advisory_all_users
print("snapshot=", snapshot_all_users.apply().result)   # {'ok': N, 'fail': 0}
print("advisory=", advisory_all_users.apply().result)    # {'ok': N, 'fail': 0}
```

### G3 게이트 — 통과해야 S4
- 등록 확인:
  ```python
  from django_celery_beat.models import PeriodicTask
  for t in PeriodicTask.objects.filter(name__in=["portfolio-snapshot-daily","portfolio-advisory-daily"]):
      print(t.name, t.task, t.enabled, t.crontab.hour+":"+t.crontab.minute, t.crontab.timezone)
  ```
  → **2행**, 스케줄 19:0 / 19:15, timezone `America/New_York`, `enabled=True`
- 수동 킥 결과 확인:
  ```python
  from datetime import date
  from apps.portfolio.models_my import PortfolioSnapshot, AdvisoryRun
  print("snapshot today=", PortfolioSnapshot.objects.filter(date=date.today()).count())  # ≥1
  print("advisory auto=", AdvisoryRun.objects.filter(trigger="auto").count())            # ≥1
  ```
  → PortfolioSnapshot 오늘 ≥1행 · AdvisoryRun `trigger=auto` ≥1행
- 실패 시: 정지. `.apply().result` 의 fail 카운트 + 태스크 로그(`stocks.log`) 보고.

## S4. sv sync (런타임 반영 — 20b REST/화면)

```bash
sv sync     # = scripts/worker_sync.sh — 런타임 3트리(worker·web·api) origin/main 정렬
            #   api 트리(daphne :18765) re-detach + 재기동 (⚠ WS 연결 순간 끊김)
```

### G4 게이트 — 통과 시 적용 완료
- knobs: `GET /api/v1/advisory/knobs/` → **200**(목표 있는 사용자) /
  `PATCH /api/v1/advisory/knobs/` 범위 내 값(예 `{"aggressiveness_offset":4}`) → **200** ·
  범위 밖(예 `99`) → **400**
- wallet: `GET /api/v1/wallet/holdings/` → **200** · `GET /api/v1/wallet/cash/` → **200**
- 화면: 코치 탭(`/advisory`) 로드 + **[지금 진단]** 1회 → `AdvisoryRun trigger="manual"` 기록 확인
  ```python
  from apps.portfolio.models_my import AdvisoryRun
  print(AdvisoryRun.objects.filter(trigger="manual").count())  # [지금 진단] 후 ≥1
  ```
- 실패 시: 정지. 응답 코드·본문(스모크) + daphne health(`sv sync` 로그의 401/403/200) 보고.

## 다음날 아침 체크리스트 (개시 완료 판정 — 디렉터 보고용)
- [ ] PortfolioSnapshot 어젯밤 1행(수동 킥 분과 date/run_at 으로 구분)
- [ ] AdvisoryRun `trigger=auto` 1행(어젯밤 19:15 ET 발화분)
- [ ] 코치 탭 기준일(`advisory/summary` 의 `date`) = 어제 날짜로 갱신
- [ ] 총자산 KRW(`total_krw`) 값 상식 범위(환율 반영 정합 — KRW 환산 총액)
- 전부 ✓ → "원장 축적 개시" 보고 / 하나라도 ✗ → 해당 쿼리 출력과 함께 보고

## 이상 시 공통 대응
- 어느 게이트든 실패 = 그 지점 정지가 정상 동작이다. 되돌리기 시도 금지(가산 스키마라 방치가 안전), 디렉터 보고 후 지시 대기.
- **순서 불변**: S1→S2→S3→S4. 특히 **S2(backfill) 실패 시 S3(beat) 미진입** — 환율 없는 상태로
  권유가 자동 생성되면 KRW 원장이 오염된다(G2 가 이 순서를 강제하는 이유).

---
### 부록 — 검증 이력(형식 검증)
이 런북의 모든 게이트 쿼리·스모크는 작성 세션(2026-07-18)에 **dev DB 에서 실제 실행돼 형식 검증**됨
(prod 실행 아님): G1 `showmigrations`(fx 0001·portfolio 0004~0006 식별) / G2 ExchangeRate 쿼리
(count=1373·min 2021-07-14·max 2026-07-13·close 1491.09) / G3 beat `--dry-run`·`.apply()`
(snapshot·advisory 각 ok=1)·PeriodicTask 조회 / G4 APIClient(knobs GET 200·PATCH 200/400·
wallet GET 200). 명령이 문법적으로 돌고 기대 형태를 반환함을 확인한 것이며 prod 상태와 무관하다.
