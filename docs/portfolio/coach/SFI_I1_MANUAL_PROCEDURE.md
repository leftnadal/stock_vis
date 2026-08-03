# SFI-I1 병진 수동 구간 절차서 (Claude 집행 금지)

> 공유 DB 절대 규칙: migrate·beat 등록·prod 태스크 실행 = **병진 수동**. Claude Code는
> 코드·마이그 파일 생성·검증까지. 아래는 랜딩(rebase→push, D-LAND-ATOMIC) **이후** 운영 단계.
> 각 단계는 **확인 쿼리로 DB 영속을 증명**(#78: 화면/명령 성공 ≠ DB 영속).

브랜치 `monorepo/sess-sfi-i1` 랜딩 완료 + prod 트리(`sv-worker-runtime`)가 해당 커밋 반영 전제.
venv = `~/Library/Caches/pypoetry/virtualenvs/stock_javis_system-_jE0wOmK-py3.12/bin/python`

---

## ① migrate — 신규 테이블 생성 (기존 테이블 무변경)

```bash
# 백업(권장) 후:
python manage.py migrate stocks 0012
```

**확인 쿼리**(테이블 존재 + 0행):
```bash
python manage.py shell -c "
from packages.shared.stocks.models import AnalystSignalSnapshot
print('table_ok rows=', AnalystSignalSnapshot.objects.count())"   # → table_ok rows= 0
```
- sqlmigrate 사전 증명 = `CREATE TABLE stocks_analyst_signal_snapshot` 단독(ALTER 0).
- 게이트 실패(기존 테이블 변경 감지) 시 **정지**.

## ② 워커 재기동 — 신규 태스크 등록 (필수, 선행)

신규 태스크 `ingest_analyst_signals`는 **워커 재시작 없이는 미등록**(unregistered).
beat 등록 전에 3트리(worker/web/api) 동기화·워커 재기동:

```bash
bash scripts/worker_sync.sh   # sv-worker-runtime → 해당 커밋 반영 + 재기동
```
**확인 쿼리**(태스크 registered):
```bash
python manage.py shell -c "
from config.celery import app
print('registered', 'apps.portfolio.tasks.ingest_analyst_signals' in app.tasks)"  # → True
```

## ③ beat 1행 등록 (18:30 ET, snapshot 19:00 앞)

```bash
python manage.py sync_analyst_signals_beat --dry-run   # 예정 확인
python manage.py sync_analyst_signals_beat             # 등록(멱등)
```
**확인 쿼리**(PeriodicTask 존재·enabled·미발화):
```bash
python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
t=PeriodicTask.objects.get(name='portfolio-analyst-signals-daily')
print('task', t.task, '| enabled', t.enabled, '| last_run', t.last_run_at)"
# → task apps.portfolio.tasks.ingest_analyst_signals | enabled True | last_run None
```
- ⚠️ beat `.update()`는 signal 미발생 → 필요 시 `PeriodicTask.objects.update_changed()` 동반(TH 교훈).

## ④ 1회 수동 태스크 실행 → 수집 증명

```bash
python manage.py shell -c "
from apps.portfolio.tasks import ingest_analyst_signals
print(ingest_analyst_signals.apply().get())"
# → {'captured': N, 'failed': .., 'skipped': .., 'halted_rate_limit': False, 'universe': 14, 'errors': {}}
```
**확인 쿼리 A**(AnalystSignalSnapshot 행 적재 — last_run 아닌 실제 DB 행):
```bash
python manage.py shell -c "
from packages.shared.stocks.models import AnalystSignalSnapshot
from django.db.models import Count
print('총행', AnalystSignalSnapshot.objects.count())
print('심볼수', AnalystSignalSnapshot.objects.values('symbol').distinct().count())
for r in AnalystSignalSnapshot.objects.values('symbol').annotate(n=Count('id'))[:20]:
    print(' ', r['symbol'], r['n'])"
```
**확인 쿼리 B**(Stock.analyst_target_price 유령필드 채움 — None→값 미러 증명):
```bash
python manage.py shell -c "
from packages.shared.stocks.models import Stock
qs=Stock.objects.exclude(analyst_target_price__isnull=True)
print('target 채워진 종목', qs.count())
for s in qs.values('symbol','analyst_target_price','analyst_rating_buy')[:10]:
    print(' ', s)"
# → coach∩Stock 종목이 target·rating 값 보유(이전엔 전부 None)
```
- 갭 8종(GEVG/IONQ/IREG/IREN/OKLL/SMR/TLN/XE)은 Stock 행 부재 시 미러 skip(스냅샷은 적재).

## ⑤ 익일 아침 자동 발화 확인 (F1 판정 패턴 재사용)

익일(다음 영업일) 18:30 ET 자동 발화 후 아침에:
```bash
python manage.py shell -c "
from packages.shared.stocks.models import AnalystSignalSnapshot
from django_celery_beat.models import PeriodicTask
import datetime
t=PeriodicTask.objects.get(name='portfolio-analyst-signals-daily')
print('last_run', t.last_run_at, '| total_run', t.total_run_count)
# last_run 아닌 실제 신규 행(당일 captured_at) 검증:
today=datetime.date.today()
print('오늘 신규행', AnalystSignalSnapshot.objects.filter(captured_at__date=today).count())"
```
- **판정**: total_run_count 증가 + **당일 captured_at 신규행 ≥ 1**(last_run 갱신만으로 green 금지 — false-green 방어).
- append 전용(D-I1-2)이라 매일 신규 행 누적 = 정상(멱등 아님, 시계열).

---

## 롤백
- 마이그: `python manage.py migrate stocks 0011` (신규 테이블 DROP, 데이터 0 손실 없음).
- beat: `PeriodicTask.objects.filter(name='portfolio-analyst-signals-daily').update(enabled=False)`.

## 절대 규칙 재확인
- estimates(analyst-estimates) **무접촉** — chain_sight `EstimateSnapshot`/주간 태스크 단일 정본(D-I1-4).
- forward_pe 미러 **제외**(FORWARD-PE-DEFER, I-2/I-3 소관).
- push·beat·migrate 전부 병진 명시 승인 인용 필수([[feedback_deploy_approval_explicit_quote]]).
