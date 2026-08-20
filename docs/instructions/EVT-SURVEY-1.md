# EVT-SURVEY-1 — EconomicEvent 공급 경로·경계 좌표 실측 (read-only)

## §0 프리플라이트
0-1. worktree ~/worktrees/sv-evt-0 (monorepo/sess-evt-0) 재사용. `git fetch origin` → HEAD·origin/main 해시 보고.
0-2. [0번 게이트] 이 지시서를 docs/instructions/EVT-SURVEY-1.md로 저장, 해당 1파일만 명시 add 커밋. push 금지.
0-3. 이후 전부 read-only. DB 쓰기·파일 수정 금지, foreground 실행, 기계 시계만(#89).

## STEP 1 — EconomicEvent 공급 경로 규명 (행이 증거)
1-1. read-only SQL: max(created_at) / max(updated_at) / 최근 30일 일별 신규 행 수(created_at 기준 일별 집계).
     → 공급이 살아있는지, 주기(일간/주간/불규칙)가 무엇인지 판정.
1-2. get_economic_calendar 호출자 전수 grep (repo 전체) — 파일·함수 목록.
1-3. refresh-market-pulse-cache 태스크 본문에서 economic calendar 수집/저장 호출 여부 확인 (추정의 실증).
1-4. config/celery.py의 update-economic-calendar dict 정의 원문 인용 (태스크 경로·주기).

## STEP 2 — 경계 좌표
2-1. macro 패키지 좌표: 절대 경로 / INSTALLED_APPS 등재명 / apps·packages 어느 트리에도 속하지 않는
     top-level인지 확인.
2-2. 의존 방향 실측: packages/shared 내 `from macro` 또는 `import macro` grep (경계 관점 — 있으면 위반 후보).
     역방향(macro→shared, macro→apps)도 grep으로 방향 지도 1장.
2-3. [관찰① 보완] packages/shared 내 이벤트/캘린더 모델 부재 확인 — EVT-SURVEY-0 §1-1 grep 원출력 첨부.

## 보고 형식
- STEP별 표. 1-1은 일별 집계를 그대로(최근 30일).
- 쓰기 = §0-2 커밋 1건뿐임을 최종 git status로 입증.

## HALT 조건 (HALT-0 기본)
- 예상 밖 조건 일체 → 즉시 HALT + 보고
