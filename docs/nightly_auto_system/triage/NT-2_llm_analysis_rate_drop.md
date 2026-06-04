# NT-2 — 뉴스 LLM 분석률 1.0% 진단 (ops 운영 풀 지시서)

- **등록일**: 2026-06-04
- **출처보고서**: 2026-06-04 Daily Report / 📰 뉴스 일일 리포트 + 💡 개선방향 6
- **분류**: ops-scoped (Celery 큐 운영 + Gemini quota — 코드 결정 아님)
- **심각도**: HIGH (24h 신규 312건 분석 막힘 → 뉴스 인텔리전스 파이프라인 사실상 정지)
- **baseline**: 🆕신규
- **목적지**: ops 운영 트리거 (본 문서) — 운영 조치만으로 풀리지 않으면 NT-2b로 승급 → `apps/news/` 코드 트랙으로 핸드오프

---

## 한 줄 문제

24h 신규 뉴스 315건 중 LLM 분석 완료 **3건(1.0%)**, **312건 pending**. importance 분포는 정상(high 3 / mid 40 / low 3, 단 mid 40 / low 3는 분석된 46건 중 분포로 보임)이므로 분석 자체가 동작 안 한 게 핵심.

## 가능한 원인 (가설 3종)

| # | 가설 | 확인 방법 | 가능성 |
|---|------|----------|--------|
| H1 | Gemini paid tier quota / 결제 상태 / API key 만료 | Gemini 콘솔 + `news.tasks` 에러 로그 | 중 |
| H2 | Celery 큐 잠금 / 워커 미가동 (특정 큐) | `celery -A config inspect active` + 워커 프로세스 | 상 |
| H3 | `news.tasks.analyze_news_with_llm` retry backoff에 막혀 다음 회차 대기 | `celery -A config inspect scheduled` + `pending` row의 retry 카운트 | 중 |

LLM 비용 리포트가 "24h $0.0009 (3 calls)"로 정상 paid tier 호출 흔적이 있으므로 **H1 quota 차단 가능성은 낮다**. H2 (워커/큐 잠김) 또는 H3 (retry stuck)가 1순위.

## STEP 0 — 실측

1. **Celery 워커 상태**
   ```bash
   ps aux | grep -E 'celery.*worker' | grep -v grep
   celery -A config inspect ping
   celery -A config inspect active_queues
   ```
   - 기대: 워커 3개(메모리 메모와 일치) + 큐 목록에 news 분석 큐 존재.
   - 의심: 분석 태스크가 매핑된 큐를 처리하는 워커가 빠졌을 수 있다.

2. **현재 실행 중·예약 태스크**
   ```bash
   celery -A config inspect active
   celery -A config inspect scheduled
   celery -A config inspect reserved
   ```
   - 분석 태스크 이름(예: `news.tasks.analyze_news_with_llm` 또는 유사) 존재 여부.
   - `scheduled`에 다량 누적이면 H3 retry stuck.

3. **DB pending 카운트 + retry 분포**
   ```bash
   poetry run python manage.py shell -c "
   from apps.news.models import NewsArticle
   from django.utils.timezone import now, timedelta
   qs = NewsArticle.objects.filter(published_at__gte=now()-timedelta(hours=24))
   print('total 24h:', qs.count())
   print('analyzed:', qs.filter(llm_analyzed=True).count())  # 필드명 실측 후 보정
   print('pending:', qs.filter(llm_analyzed=False).count())
   "
   ```
   - 실제 필드명(`llm_analyzed` / `llm_analysis_completed_at` 등)은 `apps/news/models.py` 확인 후 보정.

4. **최근 LLM 호출 로그**
   ```bash
   tail -200 stocks.log | grep -iE 'gemini|llm|analyze_news'
   grep -iE 'quota|429|RESOURCE_EXHAUSTED|invalid api key' stocks.log | tail -20
   ```

5. **Beat 스케줄에 분석 태스크 활성 여부 (DECISIONS.md 결정 = DB가 진실)**
   ```bash
   poetry run python manage.py shell -c "
   from django_celery_beat.models import PeriodicTask
   for t in PeriodicTask.objects.filter(name__icontains='news'): print(t.name, t.enabled, t.last_run_at)
   "
   ```

6. **Gemini 콘솔 확인 (사용자 손)**
   - 결제 상태 / 24h API 호출 카운트 / quota 사용량 확인.

## 조치 분기

### 경우 A: 워커가 큐 처리 안 함 (H2)
- 워커 재기동 + 큐 매핑 확인.
  ```bash
  # 메모리 lesson_celery_task_registration.md 따라 kickstart 패턴 사용
  launchctl kickstart -k gui/$(id -u)/com.stockvis.celery   # plist 이름 실측 보정
  ```
- 큐 매핑이 plist에 빠졌으면 plist 패치(사용자 손) — 패치 텍스트만 본 문서에 제공.

### 경우 B: retry stuck (H3)
- pending 312건의 `retry_count`/`last_attempt_at` 분포 확인.
- 트리거: pending 일괄 재시도 명령(태스크 실제 시그니처는 `apps/news/tasks.py` 확인 후 보정).
  ```bash
  poetry run python manage.py shell -c "
  from apps.news.tasks import analyze_news_with_llm
  from apps.news.models import NewsArticle
  from django.utils.timezone import now, timedelta
  qs = NewsArticle.objects.filter(published_at__gte=now()-timedelta(hours=24), llm_analyzed=False)
  for a in qs[:50]:  # 첫 50건 시험
      analyze_news_with_llm.delay(a.id)
  print('queued:', qs[:50].count())
  "
  ```
- 50건 처리 결과 보고 정상이면 312건 전체 재큐.

### 경우 C: Gemini quota / 결제 문제 (H1)
- 사용자 손 영역(Google Cloud 콘솔). 본 문서엔 확인 체크리스트만.
- 해소 후 경우 B의 재큐 절차로 312건 처리.

### 경우 D: Beat에서 분석 태스크가 disable / 미등록 (H3 변형)
- DB `PeriodicTask` 갱신:
  ```bash
  poetry run python manage.py shell -c "
  from django_celery_beat.models import PeriodicTask
  t = PeriodicTask.objects.get(name='news-analyze-llm')   # 이름 실측 보정
  t.enabled = True; t.save()
  from django_celery_beat.models import PeriodicTasks
  PeriodicTasks.update_changed()
  "
  ```

## 행위보존 제약

- pending 재큐 시 `delay()` 비동기로만 (메모리 lesson: 인메모리 `.apply()` 검증 금지).
- retry 카운트 강제 초기화(특정 row의 `retry_count=0` UPDATE) 금지 — 무한 retry 위험.
- Gemini API key/결제 정보는 `.env`에서 변경하지 않는다 (시크릿 보호).

## 검증

1. 30분 후 재측정:
   ```bash
   poetry run python manage.py shell -c "
   from apps.news.models import NewsArticle
   from django.utils.timezone import now, timedelta
   qs = NewsArticle.objects.filter(published_at__gte=now()-timedelta(hours=24))
   print(f'분석률: {qs.filter(llm_analyzed=True).count() / qs.count() * 100:.1f}%')
   "
   ```
   - 기대: 60% 이상(과거 회차 평균 확인 후 임계 조정).

2. 다음 야간 보고서 "📰 뉴스 일일 리포트 → LLM 분석률" 확인.

## 롤백

- 재큐만 한 경우 롤백 불요(태스크는 idempotent 가정 — `apps/news/tasks.py`에서 실측 확인 후 본 문서 주석).
- Beat 활성화 토글은 즉시 disable로 원복.

## 완료 조건

- [ ] STEP 0 결과 본 문서에 기록.
- [ ] 경우 A/B/C/D 분기 확정 + 조치.
- [ ] 다음 야간 보고서에서 분석률 ≥ 50% 회복.
- [ ] 본 사건이 운영 트리거로 풀리지 않고 코드 변경이 필요하면 **NT-2b 후속 스텁** 생성 → `apps/news/` 핸드오프.
- [ ] TASKQUEUE.md NT-2 상태 `완료` + 처리 커밋/실행 명령 해시 기록.

---

## STEP 0 결과 (2026-06-04 실측)

### 워커 상태 — 🔴 critical

`ps aux | grep celery`로 워커 4개 발견:

| PID | 시작 시각 | 명령어 | 정체 |
|-----|----------|--------|------|
| 94334 | 5/21 12:23 | `-Q neo4j --pool=solo --concurrency=1 -n` | neo4j 큐 (정식, plist 띄움) |
| 94320 | 5/26 08:48 | `-A config worker -l info --concurrency=4` | default 큐 (정식 — plist `scripts/celery-worker.sh` 매칭) |
| 56586 | 5/21 10:06 | `-A config worker -l info` | **좀비 1** — monorepo 이전(5/28) 전 코드로 떠있음 |
| 91784 | 6/1 15:38 | `-A config worker -l info` | **좀비 2** — 5/28 이후이지만 수동 띄움, 노드명 중복 |

`celery inspect ping` 응답: `DuplicateNodenameWarning: Received multiple replies from node name: celery@byeongjinui-MacBookPro.local. 2 nodes online.` — 같은 노드명에 3개 워커가 응답해 inspector가 혼란.

### Beat 스케줄 — 정상

- `analyze-news-deep-batch` (task=`services.news.tasks.analyze_news_deep`): `enabled=True`, last_run=2026-06-03 22:30, total_run=411회.
- `classify-news-batch-morning` (task=`services.news.tasks.classify_news_batch`): last_run=22:15, total_run=411회.
- 모든 뉴스 수집 / 분류 / 분석 Beat 등록 + 실행 카운트 누적 정상.

### DB pending — 🔴 critical

```
24h total (NewsArticle.published_at >= now-24h): 113
  llm_analyzed=True: 0
  llm_analyzed=False: 113
어제(48h~24h) total: 349
  llm_analyzed=True: 3
  llm_analyzed=False: 346
전체 누적: 41886
전체 llm_analyzed=True: 1085 (2.6%)
최근 분석 시점: 6/3 11:04 (1건), 6/2 22:30 (2건), 그 이전은 5/29까지 거슬러 올라감
```

### Gemini quota — 정상

- 로그(`stocks.log` + `~/Library/Logs/stockvis/celery-worker-error.log` tail 3000)에서 `quota`, `429`, `RESOURCE_EXHAUSTED`, `invalid api` 0건.
- 24h 비용 $0.0009 (3 calls) — 결제·인증 정상, 호출 자체는 가능한 상태.

### Beat ↔ 워커 import 경로 미스매치 — 🔴 ROOT CAUSE

워커 에러 로그(`~/Library/Logs/stockvis/celery-worker-error.log`)에서 결정적 단서:

```
[ERROR/MainProcess] Received unregistered task of type 'services.sec_pipeline.tasks.sync_dirty_to_neo4j'.
The message has been ignored and discarded.

Did you remember to import the module containing this task?
...
{'task': 'services.sec_pipeline.tasks.sync_dirty_to_neo4j', ...,
 'periodic_task_name': 'sec-sync-dirty-neo4j'}
```

워커가 등록한 태스크 목록(`celery -A config worker --list`로 떴을 때 표시):
```
. news.tasks.analyze_news_deep       ← 옛 경로
```

Beat가 보내는 메시지:
```
'task': 'services.news.tasks.analyze_news_deep'    ← 새 경로
```

**결론**: monorepo 재배치(2026-05-28)로 `news.tasks` → `services.news.tasks` 등 import 경로가 갱신됐다. Beat 스케줄(`PeriodicTask` DB)은 새 경로로 갱신됐고, **워커 3개 모두 그 이전·전후로 한 번 떠서 옛 경로 또는 부분 갱신 상태로 정착**. 결과:
- Beat가 보낸 분석 메시지가 워커의 미등록 태스크 → 전부 discard.
- DB pending이 누적되기만 하고 실 분석은 0건.
- 6/2 22:30에 2건 분석된 것은 그 시점에 일부 큐가 옛 경로로 동작했을 가능성(잔재).

이는 `lesson_celery_task_registration.md` (Phase 1, 2026-05-22~25 사건)와 **동일 패턴**. 메모리에 박혀 있는 교훈 그대로 재발 — monorepo 재배치 후 워커 재기동이 누락된 결과.

## 결정 분기 — 경우 E (신규 — STEP 0 결과)

**원인 확정**: Beat ↔ 워커 import 경로 미스매치 + 좀비 워커 2개. H1(quota)/H2(워커 부재)/H3(retry stuck) 모두 빗나갔다. H2의 변형 — "워커는 있는데 옛 코드라 메시지 받아도 처리 불가".

**필요 조치** (사용자 명시 승인 필요 — auto classifier 차단됨):

```bash
# 1. 좀비 워커 우아한 종료
kill -TERM 56586 91784
sleep 5
# 2. 안 죽으면 강제
kill -KILL 56586 91784 2>/dev/null || true
# 3. launchd 정식 워커 재기동 (새 import 경로로 재로드)
launchctl kickstart -k gui/$(id -u)/com.stockvis.celery-worker
# 4. 5~10초 대기 후 확인
sleep 8
celery -A config inspect ping  # "1 nodes online" 또는 "2 nodes online (default + neo4j)" 기대
# 5. 검증 — analyze_news_deep 수동 트리거
poetry run python manage.py shell -c "
from services.news.tasks import analyze_news_deep
analyze_news_deep.delay(max_articles=20)
"
# 6. 30~60초 후 DB 재측정
poetry run python manage.py shell -c "
from services.news.models import NewsArticle
from django.utils.timezone import now, timedelta
qs = NewsArticle.objects.filter(published_at__gte=now()-timedelta(hours=24))
print(f'분석률: {qs.filter(llm_analyzed=True).count() / max(qs.count(), 1) * 100:.1f}%')
"
```

**예상 결과**: 워커 재기동 즉시 새 import 경로로 재등록 → Beat 다음 회차(22:30) 또는 수동 트리거에서 즉시 처리 시작 → 24h 분석률 0% → **수십%~정상**으로 회복.

**잔여 위험**: 만약 `services.news.tasks.*` import가 코드상 깨져 있으면 워커가 startup 단계에서 죽는다. 이 경우 `~/Library/Logs/stockvis/celery-worker-error.log` 즉시 확인 + 코드 트랙(NT-2b) 승급.

**행위보존 제약**: pending 312건은 idempotent 처리 가정 — 워커 재기동 후 자동으로 재시도. 강제 재큐 명령(`for a in qs: analyze_news_deep.delay(a.id)`) 불요.

## NT-1과의 교차 (보너스 발견)

워커 에러 로그에 `sec_pipeline.tasks.sync_dirty_to_neo4j` 외에도 `mp_calc_regime_15min` retry 누적 + `FileNotFoundError(2, 'No such file or directory')` 보임 → **별도 트랙**(market pulse 데이터 파일 경로). NT-2 범위 밖, 후속 NT-7 후보.

## 후속 조치 (TASKQUEUE)

- NT-2 상태: `라우팅됨` → **`승인 대기`**. 좀비 워커 종료 + launchd 재기동 명시 승인이 필요. 사용자가 위 명령을 직접 실행하거나, ops에 자동 실행 권한을 부여한 후 재시도.
- 메모리 lesson `lesson_celery_task_registration.md` 갱신 권장: monorepo 재배치(폴더 이동)도 import 경로 변경에 해당 → 워커 재시작 필수 케이스에 추가.

---

## 조치 실행 + 후속 발견 (2026-06-04 16:17 KST)

사용자 명시 승인 받아 3단 실행 완료.

### 1단: 좀비 워커 종료 ✅
- `kill -TERM 56586 91784` → 둘 다 5초 내 정상 종료.

### 2단: launchd 워커 재기동 ✅
- `launchctl kickstart -k gui/$UID/com.stockvis.celery-worker`
- 신규 워커 PID 17499 (16:17 시작, `--concurrency=4`, plist 명령어 매칭).
- `celery inspect ping` → **2 nodes online** (celery + neo4j), DuplicateNodenameWarning 사라짐.

### 3단: 수동 트리거 + 검증
- `analyze_news_deep.delay(max_articles=20)` 큐 전송.
- 워커 로그: `Task services.news.tasks.analyze_news_deep[2023e8ec-...] received` → `succeeded in 0.08s: {'analyzed': 0, 'errors': 0, 'skipped': 20}`.
- ✅ **import 경로 미스매치 완전 해소** — 새 경로(`services.news.tasks.*`)로 정상 수신.
- 🟡 **단 20건 모두 skipped** (analyzed=0). 비즈니스 룰 차단.

### Skip 원인 분석 → 임계 설계 결과

`NewsDeepAnalyzer.analyze_batch` 로직 (services/news/services/news_deep_analyzer.py:57~107):
```python
articles = NewsArticle.objects.filter(
    published_at__gte=start_of_day,   # 오늘 KST 00:00 이후
    importance_score__isnull=False,
    llm_analyzed=False,
).order_by("-importance_score")[:max_articles]

for article in articles:
    tier = self._determine_tier(article.importance_score)   # >= 0.7 / 0.85 / 0.93
    if tier is None: skipped += 1; continue
    ...
```

오늘(6/4 KST 00:00 ~ 16:21) 신규 34건 실측:
- importance_score 채워진 것: 20건
- `>= 0.7` (Tier A 임계): **0건** → 20건 전부 skip
- importance_score null: 14건 (별도 문제 — ML/규칙 엔진 미채움)
- 상위 점수: 0.597 / 0.580 / 0.561 ... → 모두 0.7 미만

어제(24~48h) 분포 비교:
- `>= 0.7`: 3건 (= 어제 LLM 분석된 3건과 정확 일치)
- `>= 0.5`: 41건
- `>= 0.3`: 98건
- null: 236건

### 결론 — Import 미스매치는 해결, 진짜 문제 2건 분리

1. **ROOT CAUSE (import 미스매치) 완전 해결** ✅. NT-2 자체는 성공 종결.
2. **분석률 "1%"는 사실상 정상**: 시스템은 *"importance_score >= 0.7" 한정 deep 분석* 설계. Daily Report의 "24h 신규 ÷ LLM 분석" 비율 계산은 분모/분자 정의 불일치 → 보고서 지표 자체가 오해를 유발. 보고서 측 보정 권장(별도 트랙).
3. **NT-2b 후속 (코드 트랙, app:news 핸드오프)**:
   - Tier A 임계 0.7이 너무 빡빡 (어제 349건 중 3건만 통과 = 0.86%). 0.5 또는 0.55로 낮추면 일일 40건대 분석 가능.
   - importance_score null이 오늘 14/34 = 41% (어제 236/349 = 68%) → ML/규칙 엔진이 score 채움률 저조. 별도 진단 필요.
4. **잔여 unregistered task**:
   - 워커 에러 로그에 `services.news.tasks.check_pipeline_alerts` (15:30), `services.sec_pipeline.tasks.sync_dirty_to_neo4j` (16:00) — **재기동(16:17) 이전 시점**. 재기동 후 재발 여부는 다음 Beat 회차 후 확인.

### 최종 상태

- **NT-2 ROOT CAUSE**: ✅ 해결 (import 미스매치).
- **NT-2b (코드 트랙)**: 신규 등록 — Tier 임계 + importance_score null률, app:news 핸드오프.
- **NT-8 (신규)**: Daily Report 분석률 지표 정의 불일치 → 보고서 본문 생성 측 보정(사용자 손 또는 ops).
- **NT-7 (별도)**: market pulse FileNotFoundError, 이미 등록됨.
- **메모리 lesson 갱신**: `lesson_celery_task_registration.md`에 "monorepo 재배치 후 워커 재기동 누락" 케이스 추가 (Phase 1 사건과 같은 패턴 재발 — 2026-05-28 monorepo + 2026-06-04 사건).
