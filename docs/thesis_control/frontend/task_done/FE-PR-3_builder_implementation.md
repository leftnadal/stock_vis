# FE-PR-3: 대화형 빌더 — 구현 완료 보고서

> 완료일: 2026-03-13
> 브랜치: `feat/eod-dashboard-and-improvements`
> 계획 문서: `docs/thesis_control/thesis_control_phase1_frontend_FE_PR_3.md` (v3)
> 계획 리뷰: `docs/thesis_control/frontend/task_done/FE-PR-3_plan_review_v3.md`

---

## 1. 구현 완료 파일 목록 (9개)

### 신규 생성 (7개)

| # | 파일 | 역할 | 줄 수 |
|---|------|------|-------|
| 1 | `components/thesis/builder/ChatBubble.tsx` | AI/사용자 메시지 버블 (로딩 dot 애니메이션) | 37 |
| 2 | `components/thesis/builder/OptionButton.tsx` | 단일/복수 선택 버튼 (long-press 설명 지원) | 82 |
| 3 | `components/thesis/builder/MultiSelectFooter.tsx` | 복수 선택 확인 푸터 ("선택 완료 (N개) →") | 26 |
| 4 | `components/thesis/builder/TextInput.tsx` | 자동 높이 조절 텍스트 입력 (Enter 전송) | 62 |
| 5 | `components/thesis/builder/PremiseCard.tsx` | 전제 카드 (8개 카테고리 컬러맵) | 45 |
| 6 | `components/thesis/builder/ProgressBar.tsx` | 스텝 기반 진행 바 (애니메이션) | 20 |
| 7 | `lib/thesis/conversation.ts` | 빌더 상태 관리 (BuilderState, applyResponse, sessionStorage) | 113 |

### 기존 파일 수정 (2개)

| # | 파일 | 변경 내용 |
|---|------|----------|
| 8 | `app/thesis/new/page.tsx` | 전면 재작성: 6단계 대화 플로우 오케스트레이션, Mock/Real 분기, 에러 복구 | 383 |
| 9 | `lib/thesis/mock.ts` | `MOCK_CONVERSATION_START_NEWS/FREE`, `MOCK_FREE_STEP_MAP`, `MOCK_NEWS_STEP_MAP`, `MOCK_CONVERSATION_DONE` 추가 |

**총 줄 수**: ~820줄

---

## 2. 핵심 구현 사항

### 2.1 대화 플로우 (6단계 상태 머신)

```
[시작] → startConversation(entry)
  ├─ Mock: MOCK_CONVERSATION_START_{NEWS|FREE} 로드
  └─ Real: POST /thesis/conversation/start/
       ↓
[Step 1~6] AI 질문 → 사용자 응답 → sendResponse()
  ├─ 단일 선택: handleSingleSelect() → 즉시 전송
  ├─ 복수 선택: handleMultiToggle() + handleMultiConfirm()
  └─ 텍스트 입력: handleTextSubmit()
       ↓
[완료] isDone = true → 3개 완료 버튼:
  1. "좋아, 일단 달아줘" → /thesis/{id}/indicators?auto=true
  2. "내가 직접 고를래" → /thesis/{id}/indicators
  3. "나중에 할게" → /thesis
```

### 2.2 진입점 분기

| 진입점 | entry 값 | Mock 데이터 | 비고 |
|--------|----------|------------|------|
| 뉴스 기반 | `news` | `MOCK_CONVERSATION_START_NEWS` + `MOCK_NEWS_STEP_MAP` | source_news_id 전달 |
| 자유 입력 | `free_input` | `MOCK_CONVERSATION_START_FREE` + `MOCK_FREE_STEP_MAP` | 기본값 |

### 2.3 에러 처리 & 복구

- `lastRequest` 필드로 마지막 요청 저장 (H3 해결)
- `__retry__` 분기: 중간 단계 에러 시 해당 단계부터 재시도 (step 1부터 재시작 방지)
- 에러 메시지: "연결에 문제가 생겼어요. 아래 버튼으로 다시 시도할 수 있어요."

### 2.4 리뷰 피드백 반영 (v3 High 6건)

| # | 이슈 | 해결 |
|---|------|------|
| H1 | `loadConvId` 죽은 코드 | 제거, `saveConvId`/`clearConvId`만 유지 |
| H2 | StrictMode cleanup에서 conv_id 삭제 | cleanup 제거, 다음 진입 시 덮어씀 |
| H3 | `__retry__`가 항상 step 1부터 재시작 | `lastRequest` 기반 해당 단계 재시도 |
| H4 | `setTimeout` stale closure | `setState(s => ...)` 함수형 업데이트 |
| H5 | 같은 step AI 메시지 key 충돌 | `messageCounter` 기반 `generateMessageId()` |
| H6 | `conversationState` null 시점 버튼 노출 | null 가드 + 에러 재시도 UI 분리 |

---

## 3. 컴포넌트 상세

### ChatBubble.tsx
- AI 버블: `bg-gray-800 rounded-tl-sm` (좌측)
- 사용자 버블: `bg-blue-600 rounded-tr-sm` (우측)
- 로딩: 3개 bouncing dot (0ms/200ms/400ms delay)

### OptionButton.tsx
- **단일 모드**: 버튼 클릭 → 즉시 전송
- **복수 모드**: 체크박스 + 라벨 → 토글
- **Long-press**: 500ms 임계치 → BottomSheet 설명 표시
- **text_input 타입**: Pencil 아이콘 + 점선 테두리

### PremiseCard.tsx
- 8개 카테고리 컬러맵: sentiment(주황), company(초록), macro(파랑), policy(보라), technical(시안), global(노랑), supply(분홍), valuation(에메랄드)
- 선택적 삭제 버튼 (X 아이콘)

---

## 4. 의존성 & 통합

| 모듈 | 사용 방식 |
|------|----------|
| `hooks/useLongPress.ts` | OptionButton long-press 감지 (500ms) |
| `components/thesis/common/BottomSheet.tsx` | Long-press 설명 표시 |
| `lib/thesis/api.ts` | `startConversation()`, `sendMessage()` |
| `lib/thesis/mock.ts` | `USE_MOCK`, step map, 시작 응답 fixture |
| `lib/thesis/types.ts` | `ConversationButton`, `ConversationResponse`, `ConversationStartPayload` |

---

## 5. 검증 결과

- [x] `npx tsc --noEmit` — 타입 에러 0건
- [x] Mock 모드: news/free_input 양쪽 플로우 정상
- [x] 에러 → 재시도 → 복구 시나리오 정상
- [x] 복수 선택 → 확인 → 다음 단계 전환 정상
- [x] Long-press → BottomSheet → 닫기 정상
- [x] 완료 후 3개 라우팅 버튼 정상
- [x] 콘솔 에러 0건
