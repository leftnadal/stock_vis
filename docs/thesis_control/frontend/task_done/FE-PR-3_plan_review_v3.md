# FE-PR-3: 대화형 빌더 — 구현 계획 리뷰 완료 보고서 (v1→v2→v3)

> 완료일: 2026-03-12
> 브랜치: `feat/eod-dashboard-and-improvements`
> 계획 문서: `docs/thesis_control/thesis_control_phase1_frontend_FE_PR_3.md` (v3)

---

## 1. 리뷰 경과

| 버전 | 작업 | 결과 |
|------|------|------|
| v1 | 초안 작성 + 자체 검토 | 6개 이슈 발견 (R1~R6) |
| v2 | 1차 리뷰 반영 | 9개 항목 반영 (R1~R9) + 기술 결정 T3~T7 추가 |
| v3 | 2차 리뷰 반영 | 6 High + 8 Medium + 14 Low + 1 New + 6 Doc 일관성 반영 |

---

## 2. v3 반영 항목 전체 목록

### 2.1 High (6개) — 런타임 버그/데이터 손실

| # | 이슈 | 영향 | 해결 | 적용 파일 |
|---|------|------|------|----------|
| H1 | `loadConvId` 정의만 있고 호출부 없음 (죽은 코드) | 불필요 코드 | 제거. `saveConvId`/`clearConvId`만 유지 | conversation.ts |
| H2 | useEffect cleanup `clearConvId()` → StrictMode 이중 실행 시 conv_id 삭제 | dev에서 대화 시작 즉시 세션 손실 | cleanup 제거. 다음 진입 시 새 conv_id로 덮어씀 | page.tsx |
| H3 | `__retry__`가 항상 `startConversation` → 중간 진행 소실 | step 3에서 에러 → retry 시 step 1부터 재시작 | `lastRequest` 필드 (conversation.ts) + `handleSingleSelect` 내 `__retry__` 분기에서 재시도 (page.tsx) | conversation.ts, page.tsx |
| H4 | `setTimeout(() => { nextStep = state.step + 1 })` stale closure | Mock에서 step 1→3 건너뛰기 등 비결정적 동작 | `setState(s => { const nextStep = s.step + 1; ... })` 함수형 업데이트 | page.tsx |
| H5 | AI 메시지 id `ai-${step}` → modify 분기 시 같은 step 2회 → key 충돌 | React warning + 렌더링 꼬임 | `messageCounter` 기반 `generateMessageId(state, prefix)` 헬퍼 | conversation.ts, page.tsx |
| H6 | `conversationState` null 시점에 버튼 노출 | 시작 전 빈 버튼 영역 표시 | `activeButtons`에 `conversationState !== null` + `!isErrorMessage` 가드. 에러 재시도 UI는 별도 분기 (activeButtons 밖) | page.tsx |

### 2.2 Medium (8개) — UX 결함/기능 미완

| # | 이슈 | 해결 | 적용 파일 |
|---|------|------|----------|
| M1 | textarea 자동 높이 조절 미작동 | `scrollHeight` 기반 auto-resize (max 120px) | TextInput.tsx |
| M2 | step 6 mock에 buttons 3개 (죽은 데이터) | `buttons: []` + 주석 "완료 CTA 프론트 하드코딩" | mock.ts |
| M3 | CATEGORY_CONFIG에 백엔드 카테고리 누락 | 8개 (sentiment, company, macro, policy, technical, global, supply, valuation) + `DEFAULT_CATEGORY` "기타" | PremiseCard.tsx |
| M4 | BottomSheet 오버레이 클릭 시 아래 버튼 이벤트 버블링 | `e.stopPropagation()` 추가 | BottomSheet.tsx |
| M5 | ProgressBar step 0에서 0% 표시 → "시작 안 한" 느낌 | page.tsx에서 `{state.step > 0 && <ProgressBar />}` 조건부 렌더링. ProgressBar.tsx 변경 없음 | page.tsx |
| M6 | selectedIds가 에러 시에도 초기화 | `sendResponse` → `Promise<boolean>`. handleMultiConfirm: 성공 시만 `setSelectedIds([])`. handleSingleSelect/handleTextSubmit: 반환값 무시 | page.tsx |
| M7 | BottomSheet 닫기 애니메이션 없음 | 기술 부채로 명시 "열기만 slideUp, 닫기 즉시" | 섹션 5.3, 7 |
| M8 | `whitespace-pre-line` 과도한 여백 | 리스크 테이블에 기록 + 정규화 옵션 제시 | 섹션 6 |

### 2.3 Low (13개) — 코드 품질/개선

| # | 이슈 | 해결 | 적용 파일 |
|---|------|------|----------|
| L1 | OptionButton `hasExplanation` 삼항 6줄 반복 | `pressHandlers` 객체 스프레드 패턴 | OptionButton.tsx |
| L2 | EntrySource type + 배열 이중 관리 | `as const` 배열 → type 추출 단일 소스 | types.ts, page.tsx |
| L3 | `selectionToLabel` fallback이 영어 id 노출 | `(${input})` 괄호 감싸기 | conversation.ts |
| L4 | TextInput placeholder 톤 불일치 | 비반영: placeholder와 AI 메시지는 역할이 다름 (input hint vs 대화) | — |
| L5 | `useLongPress` threshold 음수/극소값 방어 없음 | `Math.max(threshold, 100)` | useLongPress.ts |
| L6 | 파일 목록에 `layout.tsx` 누락 | 수정 7개 → 총 17개로 갱신 | 섹션 1 |
| L7 | 메시지 id 생성 로직 분산 | H5와 통합, `generateMessageId` 한 곳에서 관리 | conversation.ts |
| L8 | step 1 mock에 long_press 없어 테스트 불가 | `neutral`에 `long_press_hint: true` + explanations 추가 | mock.ts |
| L9 | free_input 경로 체크리스트 누락 | 검증 시나리오 2개 추가 (textarea 표시, 텍스트 전송) | 섹션 5.2 |
| L10 | `handleComplete` Mock 404 라우팅 | mock 모드: `/thesis` 고정 + TODO 주석 | page.tsx, 섹션 5.2 |
| L11 | bounce animation JIT 클래스 확인 | 검증 항목 추가 | 섹션 5.3 |
| L12 | step 6 플로우 설명 부족 | "지표 설정 분기 (프론트 하드코딩 CTA)" 추가 | 섹션 0.4 |
| L13 | conv_id 기술 부채 문구 불명확 | H1 반영하여 문구 업데이트 | 섹션 7 |

### 2.4 신규 발견 (2개) — 리뷰 과정에서 추가 식별

| # | 이슈 | 해결 | 적용 파일 |
|---|------|------|----------|
| N1 | MOCK_STEP_MAP이 news 전용, free_input 테스트 불가 | entry별 Mock Map 분리: `MOCK_NEWS_STEP_MAP` + `MOCK_FREE_STEP_MAP` + `MOCK_FREE_CONFIRM_STEP` | mock.ts, page.tsx |

### 2.5 문서 일관성 (6개)

| # | 이슈 | 해결 |
|---|------|------|
| D1 | `page.tsx`가 "신규 생성" 카테고리에 있었음 | "기존 파일 수정"으로 이동 (v2에서 이미 반영) |
| D2 | 기술 결정 T3 취소선 Claude Code 해석 불가 | v2에서 이미 취소선 제거하고 v2 결정만 남김 (확인) |
| D3 | Claude Code 프롬프트에 v3 경고 미반영 | H4(stale closure), H5(messageCounter), H6(에러 별도 분기), H3(lastRequest), N1(entry별 Mock Map) 경고 추가 |
| D4 | 해결된 리스크 #6 취소선 노이즈 | 행 삭제 |
| D5 | `conversation.ts` "재사용 없음" 부정확 | "FE-PR-6 유사 패턴 참고 가능" |
| — | 프롬프트 v2 → v3 참조 | 제목, conversation.ts 설명, 주의사항 헤더 갱신 |

---

## 3. v3 핵심 기술 결정 (누적)

| # | 결정 | 이유 |
|---|------|------|
| T1 | sonner 도입 (Toast) | 4KB, 다크테마 기본, PR-2 코드 주석에서 권장 |
| T2 | 바텀시트: CSS transform (Framer Motion 미사용) | 1인 개발 유지보수, 의존성 최소화 |
| T3 | conv_id sessionStorage + cleanup 없음 | StrictMode 이중 실행 방지. 다음 진입 시 덮어씀 |
| T4 | 뒤로가기: 첫 step에서만 확인 | 백엔드 step rollback 미지원 |
| T5 | `useLongPress` 커스텀 훅 분리 | 롱프레스/클릭 충돌 방지 + 재사용 + 훅 단위 테스트 |
| T6 | `ENTRY_SOURCES as const` → type 추출 | 백엔드 화이트리스트와 단일 소스 유지 |
| T7 | 데스크톱 Info 아이콘 (롱프레스 대체) | 모바일 전용 제스처 → 데스크톱 접근성 보장 |

---

## 4. 파일 목록 (총 17개)

### 신규 생성 (9개)

| # | 파일 | 역할 |
|---|------|------|
| 1 | `hooks/useLongPress.ts` | 롱프레스 커스텀 훅 (재사용 가능) |
| 2 | `components/thesis/builder/ChatBubble.tsx` | AI/사용자 말풍선 + 로딩 dots |
| 3 | `components/thesis/builder/OptionButton.tsx` | 선택 버튼 (single/multi + useLongPress + Info 아이콘) |
| 4 | `components/thesis/builder/PremiseCard.tsx` | 근거 카드 (category 뱃지 8종 + fallback) |
| 5 | `components/thesis/builder/MultiSelectFooter.tsx` | 멀티 선택 완료 버튼 |
| 6 | `components/thesis/builder/TextInput.tsx` | 자유 텍스트 입력 (auto-resize) |
| 7 | `components/thesis/builder/BottomSheet.tsx` | 바텀시트 (CSS slideUp) |
| 8 | `components/thesis/builder/ProgressBar.tsx` | 상단 진행률 바 |
| 9 | `lib/thesis/conversation.ts` | 대화 상태 관리 (BuilderState, applyResponse, messageCounter, lastRequest, generateMessageId) |

### 기존 파일 수정 (8개)

| # | 파일 | 변경 내용 |
|---|------|----------|
| 10 | `lib/thesis/types.ts` | ENTRY_SOURCES, EntrySource, ConversationState, PreviewPremise, ThesisPreview |
| 11 | `lib/thesis/api.ts` | sendMessage/startConversation 시그니처 백엔드 일치 |
| 12 | `lib/thesis/mock.ts` | entry별 Mock Map (MOCK_NEWS_STEP_MAP + MOCK_FREE_STEP_MAP) |
| 13 | `components/thesis/list/EntryPointGrid.tsx` | showTemporaryToast → sonner 교체 |
| 14 | `app/thesis/layout.tsx` | `<Toaster />` 추가 |
| 15 | `app/thesis/new/page.tsx` | 대화형 빌더 페이지 전면 교체 |
| 16 | `app/globals.css` | slideUp 키프레임 추가 |
| 17 | `package.json` | sonner 의존성 추가 |

---

## 5. 발견된 주요 패턴 (구현 시 참고)

### 5.1 stale closure 방지 (H4)

```tsx
// ❌ setTimeout 안에서 state 직접 참조 — stale closure
setTimeout(() => {
  const nextStep = state.step + 1  // 캡처된 이전 값!
  setState({ ...state, step: nextStep })
}, 800)

// ✅ 함수형 업데이트로 최신 state 접근
setTimeout(() => {
  setState(s => {
    const nextStep = s.step + 1
    return { ...s, step: nextStep }
  })
}, 800)
```

### 5.2 StrictMode useEffect 이중 실행 (H2)

```tsx
// ❌ cleanup에서 삭제 → StrictMode에서 mount→cleanup→remount 시 데이터 손실
useEffect(() => {
  startConversation(entry)
  return () => clearConvId()  // 첫 mount에서 즉시 삭제됨!
}, [])

// ✅ cleanup 없이. 다음 진입 시 새 conv_id로 덮어씀
useEffect(() => {
  startConversation(entry)
}, [])
```

### 5.3 메시지 id 충돌 방지 (H5)

```tsx
// ❌ step 기반 — modify 분기 시 같은 step 2회 → key 충돌
id: `ai-${response.step}`

// ✅ 카운터 기반 — 항상 유니크
export function generateMessageId(state: BuilderState, prefix: 'ai' | 'user' | 'error'): string {
  return `${prefix}-${state.messageCounter}`
}
```

### 5.4 sendResponse boolean 반환 (M6)

```tsx
// ❌ 에러 시에도 selectedIds 초기화
await sendResponse(selectedIds, label)
setSelectedIds([])  // 에러여도 실행됨

// ✅ 성공 시에만 초기화
const success = await sendResponse(selectedIds, label)
if (success) setSelectedIds([])
```

### 5.5 EntrySource 단일 소스 (L2)

```ts
// ❌ type과 배열 이중 관리
type EntrySource = 'news' | 'free_input' | 'popular' | 'template' | 'chainsight'
const VALID_SOURCES = ['news', 'free_input', ...]  // 동기화 누락 위험

// ✅ as const 배열에서 type 추출
export const ENTRY_SOURCES = ['news', 'free_input', 'popular', 'template', 'chainsight'] as const
export type EntrySource = (typeof ENTRY_SOURCES)[number]
```

### 5.6 lastRequest 기반 재시도 (H3)

```tsx
// ❌ retry가 항상 startConversation → 중간 진행 소실
if (button.id === '__retry__') {
  startConversation(entry)  // step 3에서 에러 → step 1부터 다시!
}

// ✅ lastRequest로 동일 요청 재시도
if (button.id === '__retry__') {
  if (state.lastRequest) {
    sendResponse(state.lastRequest.user_input, state.lastRequest.label)
  } else {
    startConversation(entry)  // 시작 실패 시에만
  }
}
```

- `sendResponse`에서 API 호출 직전에 `lastRequest` 저장
- `applyResponse` 성공 시 `lastRequest: null`로 초기화
- `__retry__` 핸들러: `lastRequest` 있으면 동일 요청, 없으면 처음부터

---

## 6. 다음 단계

| 순서 | 작업 | 상태 |
|------|------|------|
| 1 | v3 계획 문서 커밋 | 대기 |
| 2 | FE-PR-3 구현 (계획 문서 기반) | 예정 |
| 3 | FE-PR-4: 지표 설정 | 예정 |

---

## 7. 관련 문서

| 문서 | 경로 |
|------|------|
| 구현 계획 (v3) | `docs/thesis_control/thesis_control_phase1_frontend_FE_PR_3.md` |
| 설계 문서 | `docs/thesis_control/thesis_control_design.md` |
| FE-PR-1 완료 보고서 | `docs/thesis_control/frontend/task_done/FE-PR-1_routing_common_components.md` |
| FE-PR-2 완료 보고서 | `docs/thesis_control/frontend/task_done/FE-PR-2_thesis_list_page.md` |
| thesis-control sub_claude_md | `sub_claude_md/thesis-control.md` |
