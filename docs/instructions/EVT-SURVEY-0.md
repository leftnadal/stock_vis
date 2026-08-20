# EVT-SURVEY-0 — 이벤트(캘린더) 트랙 사전 전수 조사 (read-only)

목적: 이벤트 트랙(D-EVT-1/2/3) 결정에 필요한 ground truth 수집.
구현·모델 생성·마이그레이션·기존 파일 수정 일절 금지.

## §0 프리플라이트
0-1. `git fetch origin` → `git worktree list`. 본 세션용 worktree가 없으면 기존
     세션 worktree 관례에 따라 생성, 브랜치명 `monorepo/sess-evt-0` (origin/main 기점).
0-2. [0번 게이트] 이 지시서 전문을 `docs/instructions/EVT-SURVEY-0.md`로 저장 후
     해당 파일 1개만 명시 add하여 커밋. `git add -A` 금지. push 금지(디렉터 지시 대기).
0-3. 기준선 실측 보고: HEAD 해시 / origin/main 해시 / `git status` 클린 여부.
0-4. 이후 모든 STEP은 read-only. DB 쓰기·파일 생성/수정·프로세스 조작 금지.
     모든 명령 foreground 실행. 시간 판단은 기계 시계만(#89).

## STEP 1 — repo 내 캘린더/이벤트 기존 자산 전수
1-1. `grep -rn --include="*.py" -iE "calendar|earnings|economic|fomc|event" packages/shared/`
     → 히트 파일·심볼 표 (테스트 파일은 별도 열로 구분).
1-2. packages/shared 내 FMP 클라이언트 래퍼가 현재 구현한 엔드포인트 메서드 전수 목록
     (메서드명 · 대응 FMP 경로).
1-3. `ipos-calendar` 소비 경로 실측: 수집 태스크명 · 저장 모델 · beat 등록명.
1-4. EstimateSnapshot 실측: 모델 정의 위치 / 최신 snapshot_date / 총 행 수 (read-only SQL).
1-5. `apps/` 전체에서 "Event" 명명 충돌 여부 (기존 Event 모델·테이블 존재 확인).

## STEP 2 — beat/파이프라인 현황
2-1. DatabaseScheduler 등록 beat 전수 중 수집성 태스크 목록: 이름 / 주기 / enabled / 시간대.
2-2. 캘린더성 수집이 얹힐 수 있는 기존 일간 파이프라인의 실행 시각 앵커(ET/KST/UTC) 정리.

## STEP 3 — FMP Starter 캘린더 접근 프로브 (G-EVT-1, 최대 ~6콜)
3-0. API 예산 원장 확인 → 잔여 캡 대비 6콜 여유 없으면 HALT.
3-1. 후보 엔드포인트 각 1콜(좁은 날짜창 파라미터, 키는 .env 직독 스크립트 — 클립보드·셸 인자 금지):
     earnings-calendar / economic-calendar 계열 / dividends-calendar /
     splits-calendar / earnings 확정(confirmed)형 존재 시 / ipos-calendar(PASS 대조군).
3-2. 각 기록: HTTP 상태 / 응답 건수 / 필드 목록(샘플 1건, 값은 요약) / 응답 캡 징후.
     402·403은 FAIL로 기록하고 계속 진행 (관찰 목적 — HALT 아님).
3-3. earnings 캘린더 PASS 시: 추정일/확정일 구분 필드 존재 여부와 필드명 명시.
     경제 캘린더 PASS 시: 이벤트 등급/국가 필터 필드 존재 여부 명시.

## STEP 4 — 프론트·하네스
4-1. Next.js 코드에서 calendar/event/earnings 관련 컴포넌트·페이지 grep 전수.
4-2. TASKQUEUE·DECISIONS에서 이벤트/캘린더 언급 항목 전수 인용.

## 보고 형식
- STEP별 표. 프로브는 엔드포인트 × (상태·건수·핵심필드) 표.
- 쓰기 작업이 §0-2 커밋 1건뿐임을 최종 `git status` + `git log --oneline -3`으로 입증.

## HALT 조건 (HALT-0 기본)
- 예산 원장 잔여 부족 / 인증 오류 연쇄(키 문제 의심) / read-only 위반이 필요한 상황
- 예상 밖 조건 일체 → 즉시 HALT + 보고
