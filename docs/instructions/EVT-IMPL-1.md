# EVT-IMPL-1 — 이벤트 트랙 구현 1호: 거버넌스 번들 + 원장 토대 (write)

전제: 디렉터 구현 금지 해제(2026-08-24). 설계 앵커 = docs/design/event_calendar_design.md v1.1
(본 세션 §0-5에서 커밋). 본 지시서가 설계 앵커와 충돌하면 즉시 HALT 후 보고.
범위 밖(금지): 수집 태스크·beat 등록·연합 읽기·FE — 2호 이후. migrate 실행·push — 사용자 수동.

## §0 프리플라이트
0-1. `git fetch origin` → origin/main 해시 보고.
0-2. 신규 worktree 생성: 브랜치 `monorepo/sess-evt-1`, origin/main 기점 (경로는 sv-evt-0 관례).
0-3. 조사 계보 통합: `monorepo/sess-evt-0`(조사 커밋 3건 b026b89b·e23b25ea·b671605d, docs만)를
     no-ff merge. 충돌 발생 시 HALT.
0-4. [0번 게이트] 본 지시서 전문 → docs/instructions/EVT-IMPL-1.md, 해당 1파일만 명시 add 커밋.
0-5. 사용자 전달 파일 event_calendar_design.md → docs/design/event_calendar_design.md 커밋.
     파일 미전달 시 HALT.
0-6. baseline: `scripts/health_check.py` 통과 확인. 전 명령 foreground, 시간 판단 기계 시계(#89),
     `git add -A` 금지(전 단계 공통), push 금지(사용자 "푸시" 지시 대기 — D-PUSH-DELEG).

## STEP 1 — 거버넌스 번들 (커밋: docs 전용)
1-1. DECISIONS.md append (설계 앵커 §1 표 6행 전문 + 이연 2건 + no-retroactive + 하드 요건).
1-2. TASKQUEUE 갱신:
     (a) :1361 SPLIT-CALENDAR-PREVIEW → 상태 "EVT 흡수(2026-08-24)" 표기, 설계 앵커 참조
     (b) IT-3(b) 항목에 주석: "earnings_within_14d 정확화는 CalendarEvent 소비로 해소 예정"
     (c) 신규 등재: [EVT-P2] Phase 2 백로그 P2-i~v + G-EVT-2 프로브 게이트 (상세 = 설계 앵커 §7)
     (d) 신규 등재: [EVT-CHAIN] Phase 2 관계망 타임라인 트랙 (상세 = 설계 앵커 §6)
     (e) 신규 등재: [OPS] FMP 영속 예산 원장 부재 — in-memory 카운터뿐 (백로그)
1-3. common-bugs.md append (부존재 판정 규율 — head -N 절단·이름 grep만으로 '없음' 판정 금지).
1-4. 위 파일들만 명시 add하여 커밋 1건.

## STEP 2 — CalendarEvent 모델 (커밋 분리)
2-1. 실측: packages/shared 내 stocks 모듈의 모델 파일 배치 관례 확인(StockSplit 정의 위치 기준).
     동일 트리에 CalendarEvent 배치. 관례가 불명확하거나 복수면 HALT 보고.
2-2. 설계 앵커 §2 스키마 그대로 구현: event_type choices(EARNINGS/DIVIDEND/SPLIT), symbol·
     event_date db_index, session, status(scheduled/occurred/stale), 유형별 nullable 필드군,
     first_seen_at/last_seen_at/date_observed_count, source/fmp_last_updated,
     unique_together(event_type, symbol, event_date), db_table 'shared_calendar_event'.
2-3. makemigrations 실행 → 생성 마이그레이션 파일 검토 + `sqlmigrate` 출력 전문 보고.
     **실 DB `migrate` 실행 금지 — 사용자 수동 단계.**
2-4. 단위 테스트: 멱등키 upsert 동작(update_or_create 중복 방지), status 전이 유효값,
     date_observed_count 증가 로직 헬퍼가 있다면 그 동작.

## STEP 3 — FMP 래퍼 + 캡 감지 유틸 (커밋 분리)
3-1. shared FMP 클라이언트에 3메서드 신규: get_earnings_calendar / get_dividends_calendar /
     get_splits_calendar (from/to 파라미터). 기존 메서드 관례(circuit breaker·에러 처리) 준수.
3-2. 캡 감지 유틸 detect_truncation(requested_from, requested_to, rows) →
     count==4000 OR 반환 date-span < 요청 span이면 True. 단위 테스트 포함.
3-3. **본 슬라이스에서 실 FMP API 호출 금지.** 테스트는 mock 픽스처만 — 필드는 SURVEY-0/2 실측 기준.

## STEP 4 — 검증 (커밋 없음)
4-1. 전체 테스트 스위트 실행 + 아키텍처 경계 테스트: shared→apps 신규 위반 0 확인.
4-2. scripts/health_check.py 통과.
4-3. 최종 보고: git log --oneline / git status 클린 / 테스트·sqlmigrate 요약 / STEP 2-1 배치 판단 근거.

## HALT 조건 (HALT-0 기본)
- 설계 앵커 충돌 / §0-3 merge 충돌 / 배치 관례 불명 / 테스트·health_check 실패 /
  마이그레이션이 기존 테이블을 건드리는 예상 밖 diff / 그 외 예상 밖 조건 일체
