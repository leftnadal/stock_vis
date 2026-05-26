# Slice 16 Part 5 종결 — E4 대화 Q&A 화면 (마지막 진입점)

> 슬라이스: Slice 16 (E2~E6 화면 복제)
> 단계: Part 5 (E4, 진입 순서 5/5) ⚠ 대화형 (마지막 진입점)
> 베이스: Part 4 종결 `3579d5e`
> 종결 commit: 본 문서 직전 P5-D 커밋
> Part 5 비용: **$0.004864** (P5-C 2콜) — 누적 Slice 16 **$0.0254128** (cap 2.54%)

---

## 0. 한 줄 결과

E4Output base only(§3 게이트 패스) + 안 C(dialog bubble) 정확 구현 + `E4Turn` 계약 신규 정립(role/content, assistant content == summary 1:1) + conversation_history 누적 useState 패턴. P5-C 실 round-trip 2턴에서 멀티턴 맥락 인식 명확 확인 — 2턴 응답이 1턴 "기술주 75% 편중"을 정확히 참조. 회귀 무손실(pytest 3172/52·vitest 23→25 files / 106→115 tests·tsc exit 0).

---

## 1. Part 5 KPI 매트릭스 — 5/5 통과

| #  | KPI | 결과 |
|---|---|---|
| P5-K1 | §3 게이트 | E4Output base only — 신규 필드 0건 (사전 실측) → §3 작업 없음 ✅ |
| P5-K2 | E4 데이터레이어 | postE4Coach + useE4Coach + E4Turn 계약 + MSW + fixture ✅ |
| P5-K3 | E4 화면 (안 C) | E4MessageBubble + useState 누적 + a11y + 6 화면 테스트 ✅ |
| P5-K4 | P5-C 실 round-trip | 2턴 모두 HTTP 200 + 봉투 정합 + 멀티턴 맥락 인식 실증 ✅ |
| P5-K5 | 회귀 | pytest 3172/52·vitest 25 files / 115 tests·tsc exit 0 ✅ |

---

## 2. §3 게이트 — 패스 (작업 없음, 3 EP 연속)

E4Output 실측 (`commentary_output.py:114~116`):
```python
class E4Output(CommentaryOutputBase):
    """E4 대화 Q&A output — base만 사용 (action_items/risk_flags 불필요)."""
```

필드 = `summary` / `key_observations` / `confidence` — base 그대로. `CommentaryCardData`에 모두 존재. 신규 0건 → §3 커밋 없음.

**E3 → E5 → E4** 3 EP 연속 자동 호환 — base 일반화 1회 + 완화 1회로 3 EP 호환 추가 작업 없이 흡수.

---

## 3. P5-A — E4 데이터레이어 + Turn 계약 신규 정립

**파일/변경**:
- `frontend/lib/coach/types.ts` — `E4Turn = {role:'user'|'assistant', content:string, [key:string]:unknown}`
  - 인덱스 시그니처는 codegen `conversation_history: { [key:string]:unknown }[]` 호환을 위한 구조 permission. 실제 turn은 role/content만 사용.
- `frontend/lib/coach/api.ts` — `postE4Coach` (E2~E5 동형)
- `frontend/lib/coach/hooks.ts` — `useE4Coach` (useMutation)
- `frontend/lib/coach/fixtures/e4.ts` 신규 — sampleE4InputEmptyHistory / sampleE4InputTwoTurnHistory / sampleE4Response
- `frontend/__tests__/mocks/handlers.ts` — defaultE4Response + mockE4Success/Error + 기본 handlers 등록 (5/6 → 6/6 EP)
- `frontend/__tests__/coach/useE4Coach.test.tsx` 신규 (3건)

### E4Turn 계약 (§0.2)
| 필드 | user turn | assistant turn |
|------|-----------|---------------|
| role | 'user' | 'assistant' |
| content | 사용자 입력 질문 원문 | E4Response.output.summary (요약만) |

assistant content에 `key_observations`를 넣지 않는 결정:
- **prompt 토큰 절약** — 멀티턴 시 observations 전체가 history 누적되면 토큰 폭증
- **content 단일 문자열 단순성** — 백엔드 dict[str, Any]에 1 필드만 사용

### 커밋
`94d7725` — `feat(s16): E4 데이터레이어 — postE4Coach + useE4Coach + E4Turn 계약 + MSW + fixture (Part 5 P5-A)`

---

## 4. P5-B — E4 화면 안 C (dialog bubble)

**파일**:
- `frontend/components/coach/E4MessageBubble.tsx` 신규 (45줄)
- `frontend/app/coach/e4/page.tsx` 신규 (190줄)
- `frontend/__tests__/coach/e4-page.test.tsx` 신규 (6건)

### E4MessageBubble — 경량 말풍선
- CommentaryCard 미사용 — 대화 UX에는 카드가 무겁다 (§0 확정)
- user 메시지: 우측 정렬, 파란색 (`bg-blue-600 text-white`)
- assistant 메시지: 좌측 정렬, 흰 카드 + summary + observations 불릿 (있을 때만) + confidence 배지 (있을 때만)
- E4Output 스키마 외 필드(action_items / risk_flags / quoted_metrics)는 받지 않음

### page.tsx — 대화 상태 관리
| 영역 | 구현 |
|------|------|
| state | `useState<ChatMessage[]>([])` — 화면 로컬 (전역 store 금지, §0 확정) |
| ChatMessage | UI용 확장 타입: role/content + (assistant 전용) observations/confidence |
| toTurns | ChatMessage[] → E4Turn[] 변환 (UI 전용 필드 strip) |
| 제출 핸들러 | `mutateAsync` await → onSuccess 시 user+assistant turn 2개 append + 입력칸 비움 (§0.2 계약) |
| portfolio context | 데모 디폴트 (`demo-portfolio-e4` + GARP + AAPL/MSFT/JNJ) — 대화 UX 집중 |
| fetched_at | 제출 시점 `new Date().toISOString()` |
| 빈 thread | `empty-state` testid + 안내 문구 |
| 로딩 | thread 하단 인라인 인디케이터 (`AI 코치가 답변을 작성하고 있습니다...`) |
| 에러 | thread 하단 `role="alert"` 박스 + **입력칸 유지** (재시도 가능) |
| a11y | `aria-live="polite"` + `aria-busy={isPending}` |
| auto-scroll | useEffect로 thread 하단 스크롤 (messages.length / isPending trigger) |
| 입력 | textarea (rows=2, maxLength=2000) + `0/2000` 카운터 + 전송 버튼 |

### 화면 테스트 6건
| # | 케이스 | 단언 |
|---|---|---|
| 1 | 빈 thread → 첫 질문 제출 | `payload.conversation_history === []` capturedBody 검증 |
| 2 | 멀티턴 (2 sequential mutates) | 2번째 payload에 1턴 user+assistant 누적, role 순서 user→assistant |
| 3 | assistant 응답 렌더 | E4MessageBubble에 summary + observations 불릿 + `신뢰도 높음` 배지 |
| 4 | user_question 빈/공백 | submit 버튼 disabled (3 케이스: 초기 / 공백만 / 정상) |
| 5 | MSW error | `role="alert"` 표시 + 입력칸 텍스트 유지 + thread empty-state 유지 |
| 6 | **E4Turn 계약 종단 검증** | 2턴 호출 시 assistant turn `content === summary`, observations 텍스트 미혼입 |

### 커밋
`3df3077` — `feat(s16): E4 대화 Q&A 화면 안 C + E4MessageBubble + 화면 테스트 6건 (Part 5 P5-B)`

---

## 5. P5-C — 실 백엔드 round-trip 실증 (멀티턴 운영 첫 검증 ⭐)

### 환경
- 엔드포인트: `POST http://localhost:18765/api/v1/coach/e4/?provider=haiku`
- 인증: dev admin JWT (admin/stock_vis123 → `/api/v1/users/jwt/login/`)
- portfolio: AAPL 40% / MSFT 35% / JNJ 25%, preset=garp

### 1턴 (빈 history, 첫 질문)
- 질문: "내 포트폴리오의 집중도가 어느 정도인가요?"
- 결과:
  - HTTP 200, 4.73s
  - summary: "포트폴리오의 집중도가 매우 높은 수준으로, 기술주 2개 종목에 75% 이상이 편중되어 있습니다."
  - confidence: high, observations 5건
  - input_tokens: 732, output_tokens: 411, **cost: $0.0022296**

### 2턴 (1턴 누적 history, 후속 질문)
- 질문: "그렇다면 어떤 종목부터 비중을 줄이는 게 좋을까요?"
- conversation_history:
  ```json
  [
    {"role": "user", "content": "내 포트폴리오의 집중도가 어느 정도인가요?"},
    {"role": "assistant", "content": "포트폴리오의 집중도가 매우 높은 수준으로..."}
  ]
  ```
- 결과:
  - HTTP 200, 5.14s
  - summary: "현재 포트폴리오 구조상 기술주 집중도 완화를 위해서는 AAPL과 MSFT 중 상대적으로 비중이 높은 종목 조정을 우선 검토할 수 있으나..."
  - confidence: medium, observations 5건
  - input_tokens: 853 (1턴 대비 +121 = history 비용), output_tokens: 488, **cost: $0.0026344**

### 멀티턴 맥락 인식 ⭐ — 명확 실증
2턴 응답이 1턴의 분석을 정확히 참조:
- **"기술주 75% 편중 상태에서"** (observation #3) — 1턴 응답의 "기술주 2개 종목에 75% 이상 편중"을 그대로 인용
- "AAPL과 MSFT 중 상대적으로 비중이 높은 종목 조정" — 1턴에서 식별한 두 종목을 직접 후보로 지목
- JNJ 25%는 "이미 헬스케어 섹터로 다각화" — 1턴 observation을 토대로 차별화

→ `E4PromptBuilder`의 conversation_history 주입 (json dump)이 운영에서 정상 작동함을 첫 검증.

### 정합 검증
| 항목 | 결과 |
|------|------|
| 봉투 `{output, llm_metadata}` (2턴 모두) | ✅ |
| E4Output base only (summary/key_observations/confidence) | ✅ |
| action_items / risk_flags / quoted_metrics 부재 | ✅ (스펙대로) |
| codegen `CoachE4Response` shape 일치 | ✅ |
| **E4Turn 계약 (content=summary)** | ✅ |
| **멀티턴 맥락 인식** | ✅ ⭐ |
| **#72 EP=E4분 충족** | ✅ |

### ledger 정합 (Step 0-A 일관 5번째·6번째 적용)
ledger 30·31행 (P5-C 자동 append):
```json
{"timestamp": "2026-05-26T06:44:31.909822+00:00", "slice": "runtime", "entry_point": "e4",
 "provider": "anthropic", "model": "claude-haiku-4-5",
 "input_tokens": 732, "output_tokens": 411, "cost_usd": 0.0022296, "fallback_from": null}
{"timestamp": "2026-05-26T06:45:00.457485+00:00", "slice": "runtime", "entry_point": "e4",
 "provider": "anthropic", "model": "claude-haiku-4-5",
 "input_tokens": 853, "output_tokens": 488, "cost_usd": 0.0026344, "fallback_from": null}
```
- E2(26) + E6(27) + E3(28) + E5(29) + E4×2(30, 31) — 5 EP 모두 동일 정합 패턴, 6 ledger entry

---

## 6. 회귀 매트릭스 (Part 4 종결 대비)

| 트랙 | Part 4 종결 (`3579d5e`) | Part 5 종결 | 변동 |
|------|--------------------------|--------------|------|
| pytest | 3172/52 | 3172/52 | 0 |
| IDENTICAL | 31/31 | 31/31 | 0 |
| vitest | 23 files / 106 tests | **25 files / 115 tests** | +2 files / +9 tests |
| tsc --noEmit | exit 0 | exit 0 | 0 |
| cost_ledger | 29행 | **31행** | +2 (P5-C 2콜 자동) |

> pytest 회귀는 759/1(part4 closing 표기)과 절대값 차이가 있는데, 본 closing은 전체 `pytest -q` 결과를 표기. 작업 동안 0 변동.

---

## 7. 커밋 (Part 5, 3건)

| Commit | 단계 | 의미 |
|---|---|---|
| `94d7725` | P5-A | feat: E4 데이터레이어 + E4Turn 계약 + MSW + fixture |
| `3df3077` | P5-B | feat: E4 화면 안 C + E4MessageBubble + 6 테스트 |
| (본 커밋) | P5-D | docs: Part 5 closing + Slice 16 종결 |

§3 작업 없어 §3 커밋 부재 — Part 3·4와 동일 형태.

---

## 8. 부채 변동 (Part 5)

- close: **#72 EP=E4분 close → #72 6/6 전건 close** (Slice 16 closing에서 #72 자체 close)
- 신규: 0건
- #71 외부 자동화 — Slice 16 전체 (Step 0 + Part 1~5) 무재발 지속. "해소" 의견 기록 (강제 close는 Slice 16 closing에서 결정).

---

## 9. HALT 발동 이력 (Part 5)

| 시점 | 유형 | 결과 |
|------|------|------|
| P5-A tsc | E4Turn interface가 codegen 인덱스 시그니처 불호환 (TS2322) | 즉시 type alias + `[key:string]: unknown` 추가로 해소, 회귀 0 |
| (그 외) | 다른 게이트 미발동 | 회귀/IDENTICAL/봉투 정합/멀티턴 맥락 모두 정상 |

---

## 10. Slice 16 종결 진입 메모

Part 5로 **#72 6/6 전건 close** + 6 코치 화면(E1~E6) 전건 완성. 별도 `closing.md`에 Slice 16 전체 종결 보고.

후속 후보 (Slice 16 closing에서 정리):
- C 리팩터링 — CommentaryCard → BaseCard + EP별 Section. **E4가 이미 전용 렌더러(E4MessageBubble) 보유** → 출발점.
- E4 대화 영속화 — 필요 시 zustand 승격 (현재 useState 의도적 선택).
- 진입점별 응답 지연 편차 — 로딩 UX 검토 입력값 (E4 4.73~5.14s, E3 ~30s, E5 9.5s).

### §3 노트 (Slice 16 closing 반영 예정)
> E4 표현은 의도적 분기 (말풍선) — base 데이터 계약은 6화면 정합 유지. 향후 통일 시도 금지.

---

## 11. 누적 비용 (Slice 16, 최종)

| Part | EP | cost | duration |
|------|----|------|---------|
| Part 1 | E2 | $0.0025416 | - |
| Part 2 | E6 | $0.0032456 | - |
| Part 3 | E3 | $0.0095064 | - |
| Part 4 | E5 | $0.0052552 | 9.50s |
| Part 5 (1턴) | E4 | $0.0022296 | 4.73s |
| Part 5 (2턴) | E4 | $0.0026344 | 5.14s |
| **누적 (최종)** | | **$0.0254128** | |
| cap $1.00 대비 | | **2.54%** | |

cap 여유 97.46% — Slice 16은 화면 복제 + base 일반화 효과로 매우 효율적.
