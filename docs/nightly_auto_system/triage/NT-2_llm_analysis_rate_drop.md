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

## STEP 0 결과 (실행 후 채움)

```
워커 상태: 
active queues: 
pending count: 
retry 분포: 
Gemini 콘솔: 
Beat 활성: 
```

## 결정 분기

```
경우: 
조치: 
재측정 분석률: 
```
