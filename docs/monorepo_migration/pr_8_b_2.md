# 지시서 — Track A: Beat 동기화 항구 해결 / Track B: PR8b-2 dead-code 판정

## 너의 역할 / 현재 위치

- main HEAD = `1a783cd`. 두 트랙 **독립**, 순서 자유.
- Track A = PR8b-1이 남긴 Beat 드리프트 항구 해결(채택: reconcile 관리 커맨드).
- Track B = fmp_client / constants reachability 판정(삭제 단정 아님).

## ⛔ 절대 규칙 (위반 시 즉시 HALT)

1. **프로덕션 DB의 PeriodicTask UPDATE는 사용자 실행.** Claude Code는 reconcile 커맨드 **작성** + **로컬 dev DB `--dry-run`/`--apply` 검증**까지만. prod DB 자동 실행 절대 금지.
2. **dead-code 삭제는 reachability 전수 확인 후에만.** "0 consumer"는 가설 — import·동적(getattr/importlib)·문자열·admin·serializer 필드·task 호출까지 전수. 애매하면 보존.
3. 행위보존: 각 변경 후 `pytest` + 경계 테스트 GREEN. 빨개지면 그 자리 HALT.
4. 메모리/지시서 경로·라인은 가설 → 실측 우선.

---

## Track A — Beat 동기화 항구 해결

### A-0. STEP 0: 스케줄러 실측 (★ 문제 존재 여부 판가름 · 보고 후 분기)

```bash
grep -rn "beat_scheduler\|BEAT_SCHEDULER\|DatabaseScheduler\|PersistentScheduler" config/
# DB row 존재 확인 (로컬 dev, read-only)
poetry run python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
names=['update-economic-indicators','update-market-indices','update-economic-calendar','refresh-market-pulse-cache','cleanup-old-macro-data']
for n in names:
    print(n, PeriodicTask.objects.filter(name=n).values_list('task',flat=True).first())
" 2>&1 | head -20
```

**분기:**

- `PersistentScheduler`(기본)거나 위 5개 name이 전부 없음(None) → **DB 동기화 불필요. 코드 갱신으로 이미 해결.** A-1 건너뛰고 A-3(문서화)만.
- `DatabaseScheduler` + row 존재(옛 경로 `macro.tasks.*` 표시) → A-1 진행.

### A-1. reconcile 관리 커맨드 작성 (채택안)

- 위치: `apps/market_pulse/management/commands/sync_beat_schedule.py` (레이아웃에 맞게).
- 동작: **settings의 `beat_schedule` dict를 source-of-truth**로, 각 entry의 `name`에 해당하는 `PeriodicTask.task` 경로를 dict 값과 일치하도록 reconcile. **idempotent**(두 번째 실행은 0 rows).
- 플래그: `--dry-run`(기본 동작 권장 — 바뀔 row를 `name: old → new`로 출력만) / `--apply`(실제 UPDATE). dict에 없는 name은 스킵+경고. dict에 있는데 DB에 없는 name도 경고(생성은 하지 않음, 보고만).
- 단위테스트: ① dry-run이 옛→새 diff를 정확히 산출 ② apply 후 재실행 시 0 rows(idempotent) ③ dict에 없는 name 무영향.

### A-2. 로컬 검증 (Claude Code 수행 가능 — dev DB 한정)

```bash
poetry run python manage.py sync_beat_schedule --dry-run   # diff 확인
poetry run python manage.py sync_beat_schedule --apply     # dev DB만
poetry run python manage.py sync_beat_schedule --dry-run   # 0 rows 재확인(idempotent)
```

- **prod 적용은 사용자 몫:** 사용자가 prod에서 `--dry-run` 확인 → `--apply` → **celery beat 재시작**. 이 절차를 보고에 명시.

### A-3. 재발 방지 문서화

- `common-bugs.md` #28에 "**task 이동/리네임 시 `sync_beat_schedule --apply` + beat 재시작 필수**" 절차 추가.
- DECISIONS에 "Beat 드리프트 = reconcile 커맨드로 항구 처리(일회용 쉘 폐기)" 1줄.
- 커밋: "PR8b Beat: sync_beat_schedule reconcile 커맨드 + #28 절차".

---

## Track B — PR8b-2 dead-code reachability 판정

### B-0. reachability 전수 (import만 보지 말 것)

```bash
# fmp_client
ast-grep run -p 'fmp_client' --lang python apps packages thesis 2>/dev/null
grep -rn "fmp_client\|FMPClient\|FmpClient" apps packages thesis tests --include="*.py"
# macro_service 도달성 (tasks/views/admin/serializer에서 호출되나)
grep -rn "macro_service\|MacroService" apps packages thesis tests --include="*.py"
# constants/insights
grep -rn "insights\|INSIGHTS" apps packages thesis tests --include="*.py" | grep -vi "test_"
# 동적/문자열 참조 보강
grep -rn "getattr\|importlib\|import_module" apps/market_pulse --include="*.py"
```

- **transitive 판정:** fmp_client → macro_service → (tasks/views?) 사슬이 살아있으면 fmp_client는 **reachable = 보존**.
- constants/insights도 동일하게 최종 소비처까지 추적.

### B-1. 판정 → 처리

| 결과                      | 처리                                                                |
| ------------------------- | ------------------------------------------------------------------- |
| reachable (살아있음)      | 보존, dead-code 아님 명시. 삭제 금지.                               |
| 0 reachable (전수 확인됨) | `git rm` 삭제(히스토리 복구 가능) → `pytest` 회귀 0 확인            |
| 애매                      | 보존 + `# deprecated: PR8c 재검토` 주석 + TASKQUEUE 등록(삭제 보류) |

### B-2. 커밋·검증

- 의미단위 커밋(보존이면 "판정만, 변경 없음" 보고 / 삭제면 "PR8b-2: dead-code 제거").
- `pytest` 3175 유지 + 경계 테스트 GREEN(우회 0 / 동결 5) 확인.
- (참고) macro/management/commands/**init**.py 빈 패키지 잔재는 **PR8c 정리 대상**으로 태깅만.

---

## 보고 산출물

- **Track A:** 스케줄러 종류, 5개 name row 존재여부, (해당 시) sync_beat_schedule 커맨드 + dry-run 출력 + idempotent 테스트 결과 + #28 절차 갱신. prod 적용 절차 명시.
- **Track B:** fmp_client·macro_service·constants reachability 표(소비처 사슬), 판정(보존/삭제/보류), 회귀 결과.
