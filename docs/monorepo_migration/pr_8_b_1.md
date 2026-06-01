# 지시서 — PR8b-1: macro 비모델 → market_pulse 분배 (실행)

## 너의 역할 / 현재 위치

- 트랙: monorepo **PR8b 진입**(macro 분배). main HEAD = `e69a6e0`. 경계 가드 **LIVE**.
- 성격: 통째 mv 아님 = **분배**. macro는 "**모델 전용 shell app**"으로 남고, 비모델 행위만 `apps/market_pulse`로 이사.
- 채택 결정: 추천 B. fred_client → `packages/shared/api_request` (B 결정, thesis는 path만 갱신). #4·#5(macro.models) **lazy 유지·보류**.

## ⛔ 절대 규칙 (위반 시 즉시 HALT)

1. **macro/models, macro/migrations, macro/apps.py, macro/**init**.py, macro/admin.py 는 건드리지 마라.** macro는 모델 shell app으로 잔존(INSTALLED_APPS 유지). admin은 자기 모델 등록이라 모델과 동거 잔존.
2. **행위보존:** 순수 이동 + import 경로 갱신만. 로직 변경 0. 이동은 가능한 한 `git mv`로 히스토리 보존.
3. config는 **실측한 라인만** 갱신. macro app_label·INSTALLED_APPS 'macro'·LLM/spectacular enum 'macro'·URL prefix `/api/v1/macro/`는 **그대로 유지**(모델 잔존이라 label 불변, prefix 불변).
4. **각 Part 후 `pytest` + 경계 테스트 GREEN 확인.** 빨개지면 그 Part에서 HALT + 보고.
5. 메모리/이 지시서 경로·라인은 **가설** → Part 0 실측 우선.
6. **이번 범위 아님:** macro/models·migrations 이동(PR8b-3), #4·#5 청소, fmp/constants dead-code 판정(PR8c).

---

## Part 0 — 실행 전 실측 (verify gate · 보고 후 Part 1)

**0-1. macro shell app 잔존 가능 확인**

```bash
grep -n "macro" config/settings.py | head      # INSTALLED_APPS 'macro' 위치(:197 기대)
grep -rn "app_label" macro/migrations | head    # migrations가 label 'macro'에 묶인 방식
```

→ models+migrations만 남겨도 macro가 정상 app으로 등록되는지. (label 'macro' 유지 = migrations history 보존)

**0-2. fred_client 의존 재확인 (shared 이동 안전성)**

```bash
grep -n "^from \|^import \|    from \|    import " macro/services/fred_client.py
```

→ fred가 import하는 외부가 `packages.shared.api_request.rate_limiter` **뿐**인지 확인. `apps`/`macro` import가 섞였으면 **HALT**(shared 이동 시 가드 위반). 예상: clean.

**0-3. config 지점 실측 라인 추출**

```bash
sed -n '39p' config/urls.py
grep -n "macro" config/celery.py          # Beat 5건 task 경로 문자열
sed -n '197p;404p' config/settings.py
sed -n '19p' config/spectacular_enums.py
```

→ **바뀌는 것 = celery Beat task 경로 문자열(macro.tasks → market_pulse.tasks)**, urls.py:39 include 대상. **그대로 = INSTALLED_APPS 'macro', enum 'macro', URL prefix**.

**0-4. 이름 충돌 점검**

```bash
ls apps/market_pulse/tasks/ apps/market_pulse/management/commands/ apps/market_pulse/services/ 2>/dev/null
```

→ macro에서 들어올 모듈명(tasks.py, fmp_client/macro_service, mgmt 3건)이 기존과 충돌하나. 충돌 시 네이밍 전략 보고.

**0-5. market_pulse → macro.models 신규 import 지점**
→ 이사 후 market_pulse가 macro.models를 import하게 될 파일 목록(app→macro, 가드 비대상이나 명시).

→ **Part 0 결과 보고 후 Part 1 진입.** 예상과 다르면(0-2 fred 오염, 0-1 label 종속, 0-4 충돌) HALT.

---

## Part 1 — 서비스 이동

- `macro/services/fred_client.py` → `packages/shared/api_request/` (`git mv`). **thesis lazy import 경로 갱신**(thesis/tasks/eod_pipeline.py:159: `macro.services.fred_client` → 새 경로).
- `macro/services/fmp_client.py` + `macro/services/macro_service.py` → `apps/market_pulse/services/` (`git mv`). macro_service의 fred/fmp import 경로 갱신.
- `pytest` + **경계 테스트 GREEN**(fred→shared가 새 위반 안 만드는지) → commit "PR8b-1a: macro services 분배 (fred→shared, fmp/macro_service→market_pulse)".

## Part 2 — entry(urls/views/serializers) 이동

- `macro/views.py`, `macro/serializers.py` → `apps/market_pulse/`. URL은 `apps/market_pulse/urls.py`에 include + **config/urls.py:39 한 줄 교체**(prefix `/api/v1/macro/` 유지).
- views/serializers가 쓰는 macro.models·서비스 import 새 경로로 갱신.
- frontend `macroService.ts` 영향 0 확인(URL 불변).
- `pytest` GREEN → commit "PR8b-1b: macro entry(views/serializers/urls) → market_pulse".

## Part 3 — tasks 이동 + Beat DB 동기화 (R6 주의)

- `macro/tasks.py` → `apps/market_pulse/tasks/` (기존 sync_indicators.py 옆, 0-4 충돌 회피).
- config/celery.py Beat 5건 task 경로 문자열 갱신.
- **common-bugs #28 (Beat schedule drift):** dict 갱신만으론 DB의 PeriodicTask가 옛 경로 유지 → 무시됨. **DB row 동기화 절차 필요**(sync command 있으면 명시, 없으면 수동 절차). **DB 변경 수행 전 보고.**
- `pytest` GREEN → commit "PR8b-1c: macro tasks → market_pulse + Beat 경로 갱신".

## Part 4 — mgmt + constants 이동

- `macro/management/commands/` 3건 → `apps/market_pulse/management/commands/`.
- `macro/constants/` → `apps/market_pulse/` (소비자 0 → **PR8c dead-code 후보 태깅**).
- `pytest` GREEN → commit "PR8b-1d: macro mgmt/constants → market_pulse".

## Part 5 — 정리·검증·보고

- **macro 잔존 확인:** `__init__.py`, `apps.py`, `models/`, `migrations/`, `admin.py` 만 남은 shell app인지 (`find macro -type f`).
- 전체 회귀 0: `pytest` **3175 passed 유지** + 경계 테스트 GREEN + **동결 5건 그대로(우회 0)**.
- health 8항목 ✅.
- docs/monorepo + DECISIONS + PROGRESS 갱신(PR8b-1 종결, 잔존=모델/마이그레이션).
- 보고: 커밋 해시 4건, 잔존 macro shell 구조, fred 새 위치, #4·#5 상태, R6 Beat 동기화 처리법.

---

## 잔존 사항 (이번 범위 아님)

- macro/models + migrations (#4·#5 동결 lazy 유지) → **PR8b-3** 트리거 대기(app_label 전략 + DB 백업/공실 확인).
- fmp_client / constants dead-code 판정 → **PR8c**.
- thesis 처분(보류, 3트리거) 확정 시 → fred 최종 위치 재검토 트리거.

## 진입 한 줄

Part 0 실측부터. 보고 후 Part 1~5 순차(각 Part GREEN 게이트). HALT 조건: 0-2 fred 오염 / 0-1 label 종속 / 0-4 충돌 / 어느 Part든 pytest·경계 RED.
