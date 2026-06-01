# 지시서 — PR8b-3 종결: macro=영구 모델앱 확정 (이동 안 함)

## 너의 역할 / 현재 위치

- 트랙: monorepo **PR8b-3** 닫기. main HEAD = `da8cf71`.
- 채택 결정: **옵션 A** — macro/models·migrations를 **옮기지 않고**, macro를 영구 "모델 전용 앱"으로 확정.
- 성격: **코드 변경 0. 문서·큐 정리만.** (모델 이동·마이그레이션·DB 작업 일체 없음.)

## ⛔ 절대 규칙 (위반 시 즉시 HALT)

1. **macro/models, macro/migrations 를 옮기거나 수정하지 마라.** state 마이그레이션·ContentType·db_table 변경 금지. 이번 작업에 `.py` 변경은 없어야 한다.
2. plan/blueprint/docs에 "PR8b-3 = macro 모델 이동" 류 **stale 서술이 있으면 삭제가 아니라 새 결정에 맞게 정정.**
3. 메모리/지시서의 BOUNDARY-3 기존 정의("모델 이동 동봉 청소")는 **틀린 전제** → 재정의 대상(Part 2).

## Part 0 — stale 서술 실측 (가벼운 fact-check)

```bash
grep -rn "PR8b-3\|PR8b3\|모델 이동\|model 이동\|BOUNDARY-3\|macro.*이동\|동봉 청소" \
  PROGRESS.md DECISIONS.md TASKQUEUE* common-bugs.md docs/ 2>/dev/null
```

→ "macro 모델을 옮긴다"를 전제하는 서술 위치 목록. 이게 Part 1·2의 정정 대상.

## Part 1 — 결정 정착 (DECISIONS / PROGRESS / plan)

- **DECISIONS.md** — PR8b-3 결정 기록:
  - "PR8b-3 = **이동 안 함**. macro = 영구 모델 전용 앱(`models/`+`migrations/`+`apps.py`+`admin.py`). **Django 정상 패턴 = 부채 아님.**"
  - 근거 3: ① prod DB·배포 보류 전제에서 영향 0 ② **모델을 market_pulse로 옮겨도 #4·#5는 안 풀림**(shared→앱 위반 그대로) ③ monorepo 목적(git 충돌 방지·비모델 정돈)은 PR8b-1에서 달성.
  - "**옵션 C(모델을 shared로 승격) = 조건부 보류**(deferred, not cancelled). 경계 STEP 0에서 소비자 이동(방향1)이 막힐 때 정공법으로 부활."
- **PROGRESS.md** — monorepo 트랙: **PR8b 전체 종결**(8b-1/8b-2/8b-3). 잔존 = **PR8c만.** macro shell = "의도된 최종 상태"로 명시(미완성 아님).
- **plan/blueprint** — Part 0에서 찾은 "모델 이동" 전제 서술을 위 결정대로 정정.

## Part 2 — BOUNDARY-3 재정의 (모델 이동에서 분리)

- **TASKQUEUE BOUNDARY-3** 갱신:
  - (기존) "macro 모델 이동 시 #4·#5 동봉 청소" → **삭제/대체**.
  - (신규) "**#4·#5 (shared→macro.models lazy) 청소 = 모델 이동 아님.** 후보: **방향1**(소비자 `stocks/services/eod_regime_calculator.py`·`eod_pipeline.py`를 market_pulse로 이동 → app→app 합법, prod DB 무관) / 방향2(dependency inversion) / C(모델 shared 승격, 조건부). **경계 STEP 0**(그 두 서비스가 market_pulse 전용인지 vs 진짜 공용인지 실측) 후 방향1↔C 결정."
- **경계 가드 문서 / common-bugs**: "#4·#5는 영구 동결 아님 — BOUNDARY-3(소비자 이동)로 청소 예정. burn-down 0 도달 경로 = #1·#2·#3(경계 트랙) + #4·#5(BOUNDARY-3)" 한 줄.

## Part 3 — 검증 · 커밋

- **코드 무변경 확인:** `git diff --stat`에 `.py` 변경 0 (docs/큐/마크다운만).
- 회귀 sanity(무변경이라 그대로여야): `pytest` → **3179 passed / 52 skipped** 유지. 경계 테스트 ✅ 우회 0 / 동결 잔여 5. health 8항목 ✅.
- 커밋(단일): "PR8b-3 종결: macro=영구 모델앱 확정(이동 안 함) + BOUNDARY-3 재정의(소비자 이동) + C 조건부 보류".

## 보고 산출물

- Part 0 stale 정정 목록(어디를 무엇으로 고쳤나)
- PR8b-3 닫힘 상태 + macro 최종 구조 재확인
- BOUNDARY-3 새 정의 전문
- 남은 트랙 = **PR8c 단일** + (참고) PR8c 묶음 후보: 빈 패키지 잔재, graph_analysis 자기참조 회귀, FMPClient 동명 3곳 절대경로 가이드, 도식 잔재
- 코드 무변경·회귀 0 확인
