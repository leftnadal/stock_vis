# Slice 16 Part 5 — E4 대화 Q&A 화면 (마지막 진입점)

## 0. 전제 / 사전 확정 사항

- 브랜치: slice16 (작업 시작 시 `git checkout slice16` 확인)
- 폼 UX: **안 C (dialog bubble)** 확정 — CommentaryCard 미사용, E4 전용 경량
  메시지 컴포넌트 사용. 단 데이터 계약(CommentaryCardData base)은 정합 유지.
- 대화 상태: **화면 로컬 useState** 확정 — 전역 store 사용 금지.
- §3 게이트: E4Output 추가 필드 0건 → §3 작업 없음 (정합 확인만).
- 커밋 분할: P5-A / P5-B / P5-C / P5-D 의미 단위 4커밋.
- 검증 풀적용: P5-C에서 실 round-trip 1콜(멀티턴) 필수.

## 0.1 실측 확정 사실 (이 지시서의 근거)

- 입력: CommentaryInputE4 (CommentaryInputBase 상속)
  - base: portfolio_id, fetched_at, preset, entry_point("e4"), holdings[]
  - 고유: user_question (str, 1~2000), conversation_history (list[dict], default [])
- 출력: E4Output(CommentaryOutputBase) — 추가 0건
  - base: summary, key_observations[], confidence
  - 화면 메인 답변 텍스트 = summary
- API: POST /api/v1/coach/e4/, IsAuthenticated
- 봉투: { output: {summary, key_observations?, confidence}, llm_metadata: {...} }
- codegen 타입: E4Request / E4Response (frontend/lib/coach/types.ts:28-30) 존재
- 서비스: run_e4_coach(input_data, provider, client, max_tokens=2000)
  - conversation_history는 json.dumps로 prompt 주입, 비면 "(없음 — 첫 질문)"
- fixture: Slice 7 e4_conversation/ fixture는 스키마 불일치 → 재사용 금지, 신규 작성.

## 0.2 turn dict 계약 (P5 신규 정립)

conversation_history 원소는 백엔드가 dict[str, Any]만 요구하므로 프론트가 형태를 정함.
**표준 형태로 고정:**
{ role: 'user' | 'assistant', content: string }

- user turn content = 사용자가 입력한 질문 원문
- assistant turn content = E4Response.output.summary (요약 텍스트만)
  → key_observations는 화면에는 렌더하되 history content에는 넣지 않음
  (prompt 토큰 절약 + content 단일 문자열 단순성)
- 전송 규칙: 새 질문 제출 시 user_question 필드에는 신규 질문만,
  conversation_history에는 그 이전까지 누적된 turns 전체를 보냄.
  응답 수신 후 user turn + assistant turn 2개를 turns 배열에 append.

## 1. P5-A — E4 데이터레이어 (커밋: feat: E4 데이터레이어 + turn 계약)

대상: frontend/lib/coach/

1. api.ts — postE4Coach 신규 (E2~E5와 동형)
   - COACH_E4_PATH = '/coach/e4/' 이미 존재 → 재사용
   - 요청 바디는 E4Request codegen 타입 준수
   - 봉투 { output, llm_metadata } 응답 파싱은 기존 EP 헬퍼 재사용
2. hooks.ts — useE4Coach 신규 (useMutation, E2~E5 훅과 동형)
3. types.ts — Turn 타입 신규 export: { role: 'user'|'assistant', content: string }
   - E4Request / E4Response alias는 이미 존재 → 재사용
4. MSW — mockE4Success / mockE4Error 핸들러 신규
   - mockE4Success 응답은 0.2.2의 봉투 형태 정확히 반영
5. fixture — CommentaryInputE4 형태 + E4Response 형태 신규 작성
   - Slice 7 e4_conversation/ fixture 변환 아님, 신규
   - conversation_history 샘플: 빈 배열 1건 + 2-turn 누적 1건
   - 복제 함정 반영: fetched_at / holdings / preset / portfolio_id 채움

KPI: postE4Coach·useE4Coach·MSW 단위 테스트 통과, tsc exit 0.

## 2. P5-B — E4 화면 안 C 구현 (커밋: feat: E4 대화 Q&A 화면 + E4MessageBubble)

대상: frontend/app/coach/e4/ + frontend/components/coach/

1. E4MessageBubble 컴포넌트 신규 (경량, CommentaryCard 미사용)
   - user 메시지: 우측 정렬 말풍선
   - assistant 메시지: 좌측 정렬 말풍선
     - summary (메인 답변)
     - key_observations[] 있으면 불릿 렌더 (graceful — 없으면 미렌더)
     - confidence 작은 배지
2. app/coach/e4/page.tsx — 대화 화면
   - useState<Turn[]>([]) 로 대화 누적 (전역 store 금지)
   - 상단: 대화 스레드 (turns 위→아래 렌더, 신규 메시지로 스크롤)
   - 하단: 질문 입력칸 + 전송 버튼
     - user_question 빈 문자열/공백 → 전송 버튼 disabled (min_length=1 정합)
     - 전송 중 로딩 상태 표시 (E4는 대화형이라 응답 지연 체감 큼)
   - 제출 핸들러:
     - fetched_at 핸들러 내부 생성, holdings nullable 자동 채움
     - conversation_history = 현재까지 turns, user_question = 신규 질문
     - 응답 수신 → user/assistant turn 2개 append, 입력칸 비움
   - AuthGuard 우회 테스트 패턴은 Slice 15 정착 패턴 재사용
3. 화면 테스트 (E5의 8건 규모 참고)
   - 빈 history 첫 질문 → payload conversation_history: [] 단언 (capturedBody)
   - 멀티턴: 1턴 응답 후 2번째 제출 시 conversation_history에 2 turn 포함 단언
   - assistant 응답 후 summary + key_observations 불릿 렌더 확인
   - user_question 빈/공백 → 전송 버튼 disabled
   - MSW error → role=alert 에러 표시
   - assistant turn content == output.summary 확인 (0.2 계약)

KPI: 화면 테스트 전건 통과, tsc exit 0.

## 3. P5-C — 실 round-trip (커밋 없음 or docs 커밋에 포함)

- JWT: admin/stock_vis123 → /api/v1/users/jwt/login/ → Bearer
- 2턴 대화 실호출:
  - 1턴: 첫 질문, conversation_history []
  - 2턴: 후속 질문, conversation_history에 1턴 user/assistant 포함
- 검증:
  - 두 호출 모두 HTTP 200, 봉투 { output, llm_metadata } 정합
  - 2번째 응답이 1턴 맥락을 인식하는지 육안 확인 (멀티턴 운영 첫 실증 ⭐)
  - 비용·지연 기록 (E4 max_tokens=2000 — E3보다 가벼울 것으로 예상)
- 결과를 P5-D closing 문서에 기록.

KPI: 2턴 모두 200, 멀티턴 맥락 인식 확인.

## 4. P5-D — Part 5 closing + Slice 16 종결 (커밋: docs: Part 5 + Slice 16 closing)

1. docs/portfolio/coach/slice16/part_5/closing.md 작성
   - P5-A/B/C 산출 요약, KPI 결과, P5-C 실측치(비용·지연·멀티턴 확인)
2. cost_ledger.jsonl — e4 / slice="runtime" 행 append (e2/e6/e3/e5에 이어 5번째)
3. 부채:
   - #72 E4 close → #72 6/6 전건 close
   - #71 외부 자동화 — Part 1~5 무재발 지속 시 "해소" 검토 의견 기록
4. Slice 16 closing 문서
   - 회귀 최종: vitest / pytest 759-1 / IDENTICAL 31/31 / tsc exit 0
   - 누적 비용 (ledger 합산, cap $1.00 대비 %)
   - 6 코치 화면(E1~E6) 전건 완성 선언
   - 후속 후보 정리:
     a) C 리팩터링 — CommentaryCard → BaseCard + EP별 Section
     (E4가 이미 전용 렌더러 보유 → 출발점)
     b) E4 대화 영속화 — 필요 시 zustand 승격 (현재 useState 의도적 선택)
     c) 진입점별 응답 지연 편차 — 로딩 UX 검토 입력값
   - §3 노트: "E4 표현은 의도적 분기 (말풍선) — base 데이터 계약은 6화면 정합 유지.
     향후 통일 시도 금지." 명시.

## 5. 회귀 / HALT 규칙

- 회귀 baseline은 작업 시작 시 실측 (vitest 통과 수 정확 확인 후 +N 기록).
- pytest 759-1 / IDENTICAL 31/31 유지.
- 스키마·봉투 불일치 발견 시 즉시 HALT 후 보고 (Slice 15 패턴).
