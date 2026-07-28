# 포렌식 — DB beat #7 `chainsight-upward-learning` 등록 주체 규명

- 문서 상태: FINAL(읽기 전용 조사). 드리프트 #7 봉인의 후속 확정판.
- 대상: `PeriodicTask(name='chainsight-upward-learning')` — 관찰 창(T-5)에서 발견된 고아 DB beat.
- 목적: ⑴ 물질화 주체·시점 판정 ⑵ 삭제 후 재물질화 방지 확인 — 목요일(§4 3틱 통과) 정식 삭제가 즉결이 되도록.
- 관련: `docs/features/chain-sight/PR_upward_loop_D2.md`(⑨-C, config dict 죽은 beat 제거), PROGRESS 2026-07-08 T-5 노트(드리프트 #7 봉인).

---

## 1. 판정문 (요약)

**DB beat #7은 nightly/mgmt 자동화가 만든 것이 아니라, `django_celery_beat`의 `DatabaseScheduler`가 기동 시 config dict(`app.conf.beat_schedule`)를 DB로 동기화하는 표준 동작이 D1 잔재 엔트리를 물질화한 것이다.**

- 주체 = **beat 프로세스 자신**(DatabaseScheduler.setup_schedule). 외부 자동화(nightly·mgmt·worker_sync·register 커맨드) **전원 무혐의**.
- 원료 = **D1(`5f6252e`, 2026-07-02 17:02)이 config dict에 넣은 `chainsight-upward-learning @ crontab(hour=11, minute=35)`** 엔트리. 이 엔트리는 **T-3(`9c92164`, 2026-07-07 10:20)이 제거하기 전까지 존재**(07-02~07-07 창).
- 물질화 시점 = **07-02~07-07 창 안의 beat 재기동** — 유력 후보 = **07-06 16:51 KST T-1 재기동(PID 66533)**(차순위 07-04 13:13 pair코드 재기동 PID 38604). 둘 다 창 내·동일 메커니즘.
- 삭제 안전 = **현 config dict에 upward 엔트리 부재**(T-3 제거) → 삭제 후 beat 재기동해도 **재물질화 안 됨**. 정식 삭제 안전.

---

## 2. 메커니즘 실측 (가설 1 — 확증)

`django_celery_beat` **2.9.0**, `CELERY_BEAT_SCHEDULER='django_celery_beat.schedulers:DatabaseScheduler'`(settings.py:494).

`schedulers.py`:
```
257  def setup_schedule(self):
258      self.install_default_entries(self.schedule)
259      self.update_from_dict(self.app.conf.beat_schedule)   # ← config dict를 DB로

472  def update_from_dict(self, mapping):
473      s = {}
474      for name, entry_fields in mapping.items():
475          entry = self.Entry.from_entry(name, app=self.app, **entry_fields)  # ← 행 물질화
...
```
- `Entry.from_entry` = `PeriodicTask.objects.update_or_create(name=..., defaults=...)` → **config dict 엔트리마다 DB 행을 생성**(없으면 create).
- `update_from_dict`는 **mapping에 있는 것만 add/update** — **dict에서 사라진 엔트리는 삭제하지 않음**. 이것이 T-3가 config dict에서 제거한 뒤에도 DB 행이 **고아로 잔존**한 이유.

→ 매 beat 기동 시 `setup_schedule → update_from_dict(app.conf.beat_schedule)`가 실행되어, 그 시점 config dict에 있던 `chainsight-upward-learning`을 DB로 물질화한다. **자동화가 아니라 beat 프로세스의 표준 동작.**

**판정 종결 3요건(§1-2 H1)**:
1. DatabaseScheduler config dict 동기화 코드 — **실측 확인**(257/259/472).
2. config-엔트리-존재 창이 재기동을 포함 — **07-02~07-07 창이 07-04·07-06 재기동을 모두 포함**(`date_created`는 django_celery_beat 2.9.0에 필드 부재라 행 직접 소급 불가 → 창으로 대체 확정).
3. T-3 제거 전 config dict에 upward 엔트리 존재 — **git 실측 확인**(아래 §3).

## 3. 원료 이력 (git 실측)

| 커밋 | author-date | config dict 변화 |
|---|---|---|
| `5f6252e` D1 | 2026-07-02 17:02 KST | **추가**: `'chainsight-upward-learning': {task: apply_upward_learning_task, schedule: crontab(hour=11, minute=35)}` (주석 "매일 11:35 ET, aggregate·decay 직후") |
| `9c92164` T-3 | 2026-07-07 10:20 KST | **제거**: 위 엔트리 삭제(⑨-C 인라인 트리거로 대체) |

→ config dict에 upward 엔트리가 **살아있던 창 = [07-02 17:02, 07-07 10:20]**. 이 창 안의 beat 기동이 물질화 원인.

## 4. 가설 2 배제 (재발 면역용 전수 grep)

`PeriodicTask`를 기록(create/save/update_or_create)하는 코드 전수 — `chainsight-upward-learning` 등록자 **0**:
- `register_chainsight_beats.py:105` update_or_create → **chainsight beat 등록하나 upward 엔트리 없음**(D2 TODO였음, 실측 확인).
- `sync_monitor_beat`·`sync_portfolio_snapshot_beat`·`setup_marketpulse_beat`·`register_credit_beats`·`register_news_av_beat` → 각 **타 앱 자체 beat**만.
- `attention_tasks.py:12` → 실행 코드 아님(docstring 예시).
- `scripts/`(worker_sync 등)·nightly → PeriodicTask **등록 로직 없음**(있는 것은 `add_kb_lessons_infra.py`의 무관 semantic-cache disable 기록뿐).

→ **nightly/mgmt/register 전원 무혐의.** 단독 경로 = DatabaseScheduler 동기화(가설 1).

## 5. 발화 이력 (총 3회)

- `total_run_count = 3`, `crontab = 35 11 * * * America/New_York`(= 00:35 KST), `enabled=False`(`date_changed=2026-07-09 00:05:24 UTC` = disable 시각), `last_run_at=None`(disable 후 리셋됨), `args/kwargs` 빈값.
- 로그 잔존(로테이션으로 1건만): `2026-07-08 00:35:28 상향 학습: {evaluated:0, ...}`(period 07-07) = **멱등 가드 실전 검증**(00:30 ⑨-C 인라인이 이미 처리 → 00:35 DB beat는 evaluated=0, 이중 상향 차단).
- 나머지 2건(07-07·07-09 00:35 KST 추정)은 error log 로테이션으로 소급 불가. total_run_count=3 + 크론 11:35 ET + disable(07-09 00:05 UTC) 역산 = **07-06·07-07·07-08 11:35 EDT(= 07-07·08·09 00:35 KST) 3회**와 정합. (관찰 시점 total 판독과 EDT/KST 변환 불확도로 물질화 정확 시점은 07-04↔07-06 재기동 사이 미세 애매 — 둘 다 창 내·동일 메커니즘이라 결론 불변.)

## 6. 삭제 안전 확인 + 절차 초안 (실행 금지 — 목요일 3틱 통과 후 사용자 호출로만)

**재물질화 방지(안전 증명)**: 현 config dict(`config/celery.py app.conf.beat_schedule`)에 `chainsight-upward-learning`·`apply_upward_learning` **엔트리 부재**(T-3 제거) → 삭제 후 beat 기동 시 `update_from_dict`가 재생성할 원료 없음. **삭제 영구.** (⑨-C 인라인 트리거는 코드 체인이라 beat와 무관 — upward 실발화 경로는 삭제 후에도 정상.)

**절차 초안**:
1. 행 스냅샷 채록(감사 보존): `name/task/crontab/enabled/total_run_count/date_changed` — 본 문서 §5가 이미 채록.
2. 삭제: `PeriodicTask.objects.filter(name='chainsight-upward-learning').delete()` (runtime 트리 shell).
3. beat 재기동 **불요**(DatabaseScheduler는 DB 변경을 다음 tick에 동적 반영 — `PeriodicTasks.changed()` 폴링). 단 정합 확인용 재기동은 무해.
4. 익일 틱 실측: upward 발화 **1회(00:30 ⑨-C 인라인만)** 유지 + 00:35 DB beat 발화 **소멸** 확인 → 삭제 종결.

## 7. 결론 계보

- 드리프트 #7 봉인(PROGRESS 2026-07-08)의 "자동화가 config dict beat를 DB로 지연 물질화한 고아 추정" → **본 포렌식으로 확정**: "자동화"의 실체 = **DatabaseScheduler 표준 동기화 동작**(외부 자동화 아님). "지연 물질화"의 실체 = D1 config 엔트리가 T-3 제거 전 창의 beat 재기동에서 물질화.
- 정리 목록 ⓐ(DB beat 정식 삭제)의 안전·절차 = 본 문서로 선완료. 실행만 목요일 3틱 통과 후 사용자 호출.
