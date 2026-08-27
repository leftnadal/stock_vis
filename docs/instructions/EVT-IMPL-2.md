# EVT-IMPL-2 — 이벤트 수집 태스크 + dry-run (write: 코드만, 원장 실쓰기 없음)

전제: 설계 앵커 = docs/design/event_calendar_design.md v1.1 (repo 내 존재 — §0-2에서 확인).
충돌 시 HALT. 범위 밖(금지): 원장 테이블 실쓰기 · beat 등록 · 연합 읽기 · FE — 3호 이후.
push는 사용자 "푸시" 지시 대기(D-PUSH-DELEG).

## §0 프리플라이트
0-1. `git fetch origin` → worktree sv-evt-1 재사용, origin/main 역머지(auto-merge 한정,
     충돌 시 HALT). HEAD·origin 해시 보고.
0-2. 의존물 존재 확인: docs/design/event_calendar_design.md v1.1 헤더 확인. 부재 시 HALT.
0-3. [0번 게이트] 본 지시서 → docs/instructions/EVT-IMPL-2.md 커밋(1파일 명시 add).
0-4. 전 명령 foreground · 기계 시계(#89) · `git add -A` 금지 · health_check baseline 기록.

## STEP 1 — 거버넌스 소반영 (docs 커밋)
1-1. common-bugs.md append: "지시서 파일 의존물 규율 — 의존 파일은 정확한 배치 경로 +
     §0 존재 확인 스텝을 명문화. 사례: EVT-IMPL-1 §0-5 HALT(전달 경로 미명시)"
1-2. DECISIONS.md append: "D-EVT-SCOPE-U(2026-08-24): 캘린더 수집은 전량 저장, 필터는
     소비 계층. 근거: RC distinct 1,126 > 유니버스 503 — EVT-CHAIN 이웃 커버리지"

## STEP 2 — detect_truncation 재설계 (관찰① 처방)
2-1. 절단 판정 = **count ≥ 4000 단독 조건**으로 축소 (45일 청킹에서 캡이 유일한 절단
     기전 — 실측 시그니처 근거).
2-2. min_date > from + 5일은 절단이 아니라 **span_anomaly 경고 로그**로 강등(재시도·실패
     마킹 없음). 주말·휴일 시작 창의 정상 지연을 오탐하지 않기 위함.
2-3. 테스트 갱신·추가: (a) 주말 시작 창(min_date=from+3, count 소량) → False
     (b) 캡 도달 → True (c) 경고 로그 발화 케이스.

## STEP 3 — collect_calendar_events 태스크 구현
3-0. 배치 실측: packages/shared 내 celery task 선례 유무 / run-eod-pipeline 태스크 거주
     앱 확인. 규칙: shared 선례 있으면 shared 동거, 없으면 EOD 파이프라인 거주 트리에
     배치(수집 오케스트레이션 선례). 판단 근거 보고, 불명확·복수 관례면 HALT.
3-1. 구조(앵커 §3): 성분 4개 — earnings 선행 45일×2 청킹 / dividends 90일 /
     splits 90일 / earnings 트레일링 10일. 성분별 try/except 격리, 성분별
     성공·실패·행수 카운터. dry_run=True 플래그: fetch·정규화·would-be 카운터까지,
     **DB 쓰기 0**.
3-2. 청킹 경계 규약: [D0, D0+44] · [D0+45, D0+89] — 갭·중복 없음을 테스트로 고정
     (off-by-one 방지).
3-3. upsert 의미론(비-dry_run 경로 — 코드는 이번에 완성, 실행은 3호):
     - 신규: status=scheduled, first_seen=now, date_observed_count=1
     - 재관측: 필드 갱신 + last_seen=now + count+=1 (record_observation 헬퍼 경유)
     - eps_actual이 null→값 전이 시 status=occurred
     - session: 응답에 시각/세션 필드가 실재하면 매핑, 없으면 UNKNOWN (필드 실측 보고)
3-4. stale 스윕(비-dry_run): 선행 창 내 scheduled 행 중 last_seen_at < 금회 run 시작 →
     stale. **가드(하드)**: 해당 유형의 금회 fetch 성분이 성공한 경우에만 그 유형을
     스윕 — API 실패가 대량 오염 stale을 만드는 것을 차단. 가드 테스트 필수.
3-5. 시간 앵커: event_date는 FMP(ET) 원문 그대로, seen_at류는 UTC(기계 시계).

## STEP 4 — 단위 테스트 (mock, 실쓰기는 테스트 DB만)
upsert 3전이(신규/재관측/occurred) · stale 가드(성분 실패 시 스윕 0) · 청킹 경계 ·
dry_run 무쓰기 보장 · 재설계 detect_truncation 케이스.

## STEP 5 — dry-run 실측 (실 FMP 최대 6콜 인가, 원장 쓰기 0)
5-0. 예산 확인(원장 부재 — in-memory 카운터 기준) → 여유 확인.
5-1. dry_run=True 전체 1회 foreground 실행 (5콜: 45d×2 + div + splits + trailing).
5-2. 보고: 성분별 행수 / 절단 판정 결과(전부 False 기대) / span_anomaly 발화 여부 /
     샘플 3행(유형별 1) / session 필드 실측 결과 / distinct symbol 수와
     유니버스·RC 교집합 수(전량 저장 결정의 사후 확인 재료).

## STEP 6 — 검증·보고
전체 스위트 + 경계 테스트 + health_check (신규 이상 0). git log·status.
보고: STEP별 표 + 3-0 배치 판단 + 5-2 dry-run 표.

## HALT 조건 (HALT-0 기본)
앵커 충돌 / §0-1 머지 충돌 / 3-0 배치 관례 불명 / 테스트·health 실패 /
dry-run에서 절단 판정 True 또는 스키마 예상 밖 필드 구조 / 예상 밖 일체
