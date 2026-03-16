# FE-PR-6: 알림 + 마감 + API 수정 + QA — 완료 보고서

> 완료일: 2026-03-14
> 브랜치: `feat/eod-dashboard-and-improvements`
> 설계 문서: `docs/thesis_control/thesis_control_phase1_frontend_FE_PR_5.md` 내 PR-6 섹션

---

## 1. 구현 완료 파일 목록 (20개)

### 신규 생성 (6개)

| # | 파일 | 역할 | 줄 수 |
|---|------|------|-------|
| 1 | `components/thesis/alerts/AlertFilterTabs.tsx` | 전체/안읽은/읽은 3탭 필터 | 35 |
| 2 | `components/thesis/alerts/EmptyAlerts.tsx` | 필터별 빈 상태 메시지 3종 | 23 |
| 3 | `components/thesis/alerts/AlertCard.tsx` | 알림 카드 (severity 배지 + 읽음 처리) | 67 |
| 4 | `components/thesis/close/OutcomeSelector.tsx` | 적중/빗나감/미확정 카드형 라디오 | 72 |
| 5 | `components/thesis/close/CloseConfirmDialog.tsx` | 되돌릴 수 없음 경고 + 마감 확인 | 52 |
| 6 | `lib/thesis/mutations.ts` | 통합 mutation 훅 (지표 3 + 알림 1 + 마감 1) | 85 |

### 기존 파일 수정 (12개)

| # | 파일 | 변경 내용 |
|---|------|----------|
| 7 | `lib/thesis/types.ts` | `AlertListResponse`, `CloseResponse` 추가, `ThesisAlert`에 `severity`/`is_pushed` 추가, `source_entry` → `entry_source` rename |
| 8 | `lib/thesis/api.ts` | `listAlerts()` 반환타입 `AlertListResponse`, `close()` PATCH→POST + `CloseResponse` |
| 9 | `lib/thesis/mock.ts` | MOCK_ALERTS에 `severity`/`is_pushed` 추가, `MOCK_ALERT_LIST_RESPONSE` 래퍼, `entry_source` rename |
| 10 | `lib/thesis/queries.ts` | `useAlerts()` 파라미터 변경 + `.alerts` 언래핑, `useUnreadAlertCount()` → `unread_count` 직접 사용, QUERY_KEYS.alerts 단순화 |
| 11 | `lib/thesis/utils.ts` | `severityToStyle()` 함수 추가 |
| 12 | `app/thesis/(list)/page.tsx` | `useAlerts` 호출 시그니처 변경 |
| 13 | `app/thesis/(list)/alerts/page.tsx` | placeholder → 알림 페이지 전체 구현 |
| 14 | `app/thesis/[thesisId]/close/page.tsx` | placeholder → 마감 페이지 전체 구현 |
| 15 | `app/thesis/new/page.tsx` | BottomSheet import 경로 변경 |
| 16 | `app/thesis/[thesisId]/indicators/page.tsx` | mutations import 경로 변경 |
| 17 | `components/thesis/indicators/AddIndicatorSheet.tsx` | BottomSheet import 경로 변경 |
| 18 | `thesis/serializers/monitoring_serializers.py` | `ThesisAlertSerializer.fields`에 `'thesis'` 추가 (백엔드 1줄) |

### 이동 (1개)

| # | 파일 | 변경 내용 |
|---|------|----------|
| 19 | `components/thesis/builder/BottomSheet.tsx` → `components/thesis/common/BottomSheet.tsx` | 3곳 공유를 위한 공통화 |

### 삭제 (1개)

| # | 파일 | 이유 |
|---|------|------|
| 20 | `lib/thesis/indicatorMutations.ts` | `mutations.ts`로 통합 |

---

## 2. API 불일치 수정 상세 (4건)

### A. Alert 응답 형식

| | 변경 전 | 변경 후 |
|---|---------|---------|
| 백엔드 응답 | `{ alerts: [], unread_count: N }` | 변경 없음 |
| 프론트 타입 | `ThesisAlert[]` | `AlertListResponse { alerts, unread_count }` |
| `useAlerts()` | 배열 직접 반환 | `response.alerts` 언래핑 |
| `useUnreadAlertCount()` | 클라이언트 `.filter(!is_read).length` | `data?.unread_count` 직접 사용 |

### B. Close HTTP 메서드

| | 변경 전 | 변경 후 |
|---|---------|---------|
| 메서드 | `PATCH` | `POST` |
| 반환타입 | `Thesis` | `CloseResponse { status, thesis_id }` |

### C. Alert serializer 누락

| | 변경 전 | 변경 후 |
|---|---------|---------|
| fields | `'id', 'alert_type', 'severity', ...` | `'id', 'thesis', 'alert_type', 'severity', ...` |

### D. `source_entry` → `entry_source`

| 파일 | 변경 |
|------|------|
| `types.ts` | `Thesis.source_entry` → `Thesis.entry_source` |
| `mock.ts` | MOCK_THESES 3곳 → `entry_source` |

`grep -r source_entry frontend/` 실행 결과: `types.ts` + `mock.ts` 2개 파일만 사용 확인.

---

## 3. 알림 페이지 설계 (Phase B)

### 3.1 AlertFilterTabs

| 탭 | 라벨 | 필터 로직 |
|----|------|----------|
| all | "전체" | 전체 알림 |
| unread | "안읽은 알림 (N)" | `!is_read` |
| read | "읽은 알림" | `is_read` |

- 선택된 탭: `bg-blue-600 text-white`
- 비선택 탭: `bg-gray-800 text-gray-400`

### 3.2 AlertCard

| 영역 | 내용 |
|------|------|
| 상단 좌 | severity 배지 (severityToStyle) + 상대 시간 (relativeTime) |
| 중단 | 제목 (Link → /thesis/{alert.thesis}) + 메시지 (line-clamp-2) |
| 상단 우 | "읽음" 버튼 (안읽은 알림만) |

**severity 스타일**:

| severity | label | className |
|----------|-------|-----------|
| critical | 긴급 | `text-red-400 bg-red-900/30` |
| warning | 주의 | `text-yellow-400 bg-yellow-900/30` |
| info | 정보 | `text-blue-400 bg-blue-900/30` |

**읽음/안읽음 시각 구분**:
- 안읽음: `bg-gray-900 border-gray-700`
- 읽음: `bg-gray-900/30 border-gray-800` (더 투명)

### 3.3 EmptyAlerts

| 필터 | 메시지 |
|------|--------|
| all | "아직 알림이 없어요" |
| unread | "읽지 않은 알림이 없어요" |
| read | "읽은 알림이 없어요" |

Bell 아이콘 + 중앙 정렬 텍스트.

### 3.4 alerts/page.tsx Flow

```
마운트
├── useAlerts({ enabled: !USE_MOCK })
├── Mock 모드
│   ├── MOCK_ALERTS + mockReadIds(로컬 상태)로 읽음 처리
│   └── setMockReadIds로 즉시 UI 반영
├── 실제 모드
│   └── useMarkAlertRead().mutate(alertId) → 캐시 무효화
├── AlertFilterTabs (전체/안읽은/읽은)
├── filtered 알림 목록
│   ├── 0개 → EmptyAlerts(filter)
│   └── N개 → AlertCard 리스트
└── AlertBell 카운트
    └── useUnreadAlertCount → mockReadIds 변경 시 자동 감소 (Mock)
```

---

## 4. 마감 페이지 설계 (Phase C)

### 4.1 OutcomeSelector

| outcome | 아이콘 | label | 부제 | 활성 색상 |
|---------|--------|-------|------|----------|
| correct | CheckCircle | 적중 | "가설대로 흘러갔어요" | green-500 border + green-900/20 bg |
| incorrect | XCircle | 빗나감 | "예상과 다르게 흘러갔어요" | red-500 border + red-900/20 bg |
| neutral | MinusCircle | 미확정 | "아직 판단하기 어려워요" | gray-500 border + gray-800/50 bg |

카드형 라디오: 선택 시 border + bg 색상 변경, 비선택 시 `border-gray-700`.

### 4.2 CloseConfirmDialog

- BottomSheet 래퍼 사용
- 경고: AlertTriangle + "마감하면 되돌릴 수 없어요" (yellow 배경)
- "마감하기" 버튼: `bg-red-600`, `isClosing` 시 Loader2 spin + disabled
- "취소" 버튼: `isClosing` 시 disabled
- `isClosing` 중 BottomSheet onClose 차단 (실수 닫기 방지)

### 4.3 close/page.tsx Flow

```
마운트
├── useThesis(thesisId)
├── isClosed 판정 (mockClosed || thesis.status === 'closed')
│
├── isClosed === true → 읽기전용 요약
│   ├── outcome 아이콘 + 라벨 (OUTCOME_DISPLAY 매핑)
│   ├── 가설 제목
│   ├── 마감 메모 (있으면)
│   ├── 마감일 (있으면)
│   └── "목록으로 돌아가기" 버튼
│
└── isClosed === false → 마감 진행
    ├── 가설 정보 (제목 + ThesisBadge)
    ├── OutcomeSelector (outcome 선택)
    ├── outcome_note textarea (선택 입력)
    ├── "마감하기" 버튼 (outcome 미선택 시 disabled)
    │   └── CloseConfirmDialog 오픈
    │       ├── onConfirm
    │       │   ├── Mock: 500ms 딜레이 → mockClosed=true → toast
    │       │   └── 실제: closeMutation.mutateAsync → await invalidateQueries → router.push('/thesis')
    │       └── onError: isClosing 해제 + toast.error (mutation onError 자동)
    └── "돌아가기" 링크
```

---

## 5. 리팩토링 상세 (Phase D)

### 5.1 BottomSheet 공통화

| 사용처 | 변경 전 import | 변경 후 import |
|--------|-------------|-------------|
| `app/thesis/new/page.tsx` | `@/components/thesis/builder/BottomSheet` | `@/components/thesis/common/BottomSheet` |
| `components/thesis/indicators/AddIndicatorSheet.tsx` | `@/components/thesis/builder/BottomSheet` | `@/components/thesis/common/BottomSheet` |
| `components/thesis/close/CloseConfirmDialog.tsx` | — (신규) | `@/components/thesis/common/BottomSheet` |

`builder/BottomSheet.tsx` 삭제 완료.

### 5.2 Mutations 파일 통합

| 변경 전 | 변경 후 |
|---------|---------|
| `indicatorMutations.ts` (3개 훅) | `mutations.ts` (5개 훅) |

통합된 mutations.ts 구조:
```
mutations.ts
├── 지표 Mutations (indicatorMutations.ts에서 이동)
│   ├── useAddIndicator(thesisId)
│   ├── useRemoveIndicator(thesisId)
│   └── useToggleIndicator(thesisId)
├── 알림 Mutations (신규)
│   └── useMarkAlertRead()     → alerts + alertsCount 캐시 무효화
└── 마감 Mutations (신규)
    └── useCloseThesis(thesisId)  → list + detail + dashboard 캐시 무효화
```

Import 경로 업데이트: `indicators/page.tsx` 1곳.

---

## 6. 캐시 무효화 전략

### useMarkAlertRead

```ts
onSuccess: () => {
  qc.invalidateQueries({ queryKey: QUERY_KEYS.alerts })
  qc.invalidateQueries({ queryKey: QUERY_KEYS.alertsCount })
}
```

alerts (목록) + alertsCount (벨 아이콘) 양쪽 갱신.

### useCloseThesis

```ts
onSuccess: async () => {
  await Promise.all([
    qc.invalidateQueries({ queryKey: QUERY_KEYS.list }),
    qc.invalidateQueries({ queryKey: QUERY_KEYS.detail(thesisId) }),
    qc.invalidateQueries({ queryKey: QUERY_KEYS.dashboard(thesisId) }),
  ])
}
```

`await` 사용: 캐시 갱신 완료 후 리디렉트 → 목록에서 마감 상태 즉시 반영.

---

## 7. QUERY_KEYS 변경

| 키 | 변경 전 | 변경 후 |
|----|---------|---------|
| alerts | `(id?: string) => ['thesis', 'alerts', id ?? 'all']` | `['thesis', 'alerts']` |
| alertsCount | `['thesis', 'alerts-count']` | 변경 없음 |

alerts에서 옵셔널 thesisId 파라미터 제거. 백엔드가 전체 알림 목록만 반환.

---

## 8. Mock 데이터 변경

### ThesisAlert 필드 추가

| 필드 | 값 (alert-1) | 값 (alert-2) | 값 (alert-3) |
|------|-------------|-------------|-------------|
| severity | info | warning | critical |
| is_pushed | false | false | false |

### MOCK_ALERT_LIST_RESPONSE

```ts
export const MOCK_ALERT_LIST_RESPONSE: AlertListResponse = {
  alerts: MOCK_ALERTS,
  unread_count: MOCK_ALERTS.filter(a => !a.is_read).length,
}
```

### MOCK_THESES entry_source

3곳 모두 `source_entry` → `entry_source`로 변경.

---

## 9. 기술 검증 결과

| 검증 항목 | 결과 |
|----------|------|
| `tsc --noEmit` | 에러 0건 |
| `npm run build` | 성공 (19/19 페이지) |
| 백엔드 serializer 변경 | `'thesis'` 필드 추가 완료 |

### 브라우저 테스트 시나리오

| 테스트 | 검증 항목 | 결과 |
|--------|----------|------|
| `/thesis` | 목록 정상, useAlerts 시그니처 변경 후 정상 | 통과 |
| `/thesis/alerts` 전체탭 | 3개 알림, severity 배지 (정보/주의/긴급) | 통과 |
| `/thesis/alerts` 안읽은탭 | 3개 → 안읽은 알림만 표시, 카운트 정확 | 통과 |
| `/thesis/alerts` 읽음 처리 | Mock: mockReadIds 업데이트 → 읽은 알림으로 이동 | 통과 |
| `/thesis/alerts` 전부 읽음 | "읽지 않은 알림이 없어요" 빈 상태 | 통과 |
| `/thesis/mock-1/close` | OutcomeSelector 선택 → 메모 → 확인 → Mock 마감 | 통과 |
| `/thesis/mock-1/close` 읽기전용 | mockClosed=true 후 읽기전용 요약 표시 | 통과 |
| 전체 콘솔 | 에러 0건 | 통과 |

---

## 10. 설계 결정

| 결정 | 선택 | 근거 |
|------|------|------|
| Mutation 파일 통합 | `mutations.ts` 1개 | Phase 3에서 mutation 추가 시 파일 증식 방지 |
| BottomSheet 위치 | `common/` | builder/indicators/close 3곳 공유, Phase 2 마무리 적기 |
| highlight 파라미터 | 제외 (TODO 주석) | 대시보드에 수신 로직 없음, Phase 3 구현 |
| entry_source 통일 | 프론트를 백엔드에 맞춤 | 타입 레벨 해결, 주석 미사용 |
| 마감 리디렉트 | `await invalidateQueries` 후 | 캐시 먼저 갱신 → 목록에서 마감 상태 즉시 반영 |
| 에러 상태 | CloseConfirmDialog isClosing 해제 + toast | mutation onError에서 자동 처리 |
| Mock 읽음 처리 | `mockReadIds` Set (로컬) | API 없이 즉시 UI 피드백 |
| useUnreadAlertCount | 백엔드 unread_count 직접 사용 | 클라이언트 필터링 제거, 백엔드 신뢰 |

---

## 11. 의존성 그래프

```
Phase A: API/타입 수정
types.ts (AlertListResponse, CloseResponse, severity, is_pushed, entry_source)
    ├→ api.ts (listAlerts 반환타입, close POST)
    ├→ mock.ts (MOCK_ALERTS 필드 추가, MOCK_ALERT_LIST_RESPONSE)
    ├→ queries.ts (useAlerts 언래핑, useUnreadAlertCount 단순화)
    └→ utils.ts (severityToStyle)

Phase B: 알림 페이지
queries.ts (useAlerts) + mutations.ts (useMarkAlertRead)
    ├→ AlertFilterTabs.tsx
    ├→ AlertCard.tsx ← utils.ts (severityToStyle, relativeTime)
    ├→ EmptyAlerts.tsx
    └→ alerts/page.tsx

Phase C: 마감 페이지
queries.ts (useThesis) + mutations.ts (useCloseThesis)
    ├→ OutcomeSelector.tsx
    ├→ CloseConfirmDialog.tsx ← common/BottomSheet.tsx
    └→ close/page.tsx

Phase D: 리팩토링
builder/BottomSheet.tsx → common/BottomSheet.tsx
indicatorMutations.ts → mutations.ts (통합)
```

---

## 12. Phase 2 완료 상태 요약

PR-6으로 Thesis Control Phase 2 프론트엔드가 완료됨.

| PR | 범위 | 상태 |
|----|------|------|
| FE-PR-1 | 라우팅 7개 + 공통 컴포넌트 5개 + authAxios | 완료 |
| FE-PR-2 | 가설 목록 + 오늘의 변화 + 진입점 | 완료 |
| FE-PR-3 | 대화형 빌더 (뉴스/자유입력 2경로) | 완료 |
| FE-PR-4 | 지표 설정 (CRUD + AI 추천) | 완료 |
| FE-PR-5 | 관제실 대시보드 (달/화살표/트렌드) | 완료 |
| FE-PR-6 | 알림 + 마감 + API 수정 + QA | 완료 |

### 전체 파일 수

| 카테고리 | 파일 수 |
|---------|---------|
| 페이지 (`app/thesis/`) | 8 (layout 2 + page 6) |
| 컴포넌트 (`components/thesis/`) | 22 |
| 라이브러리 (`lib/thesis/`) | 8 |
| **합계** | **38** |

---

## 13. 기술 부채

| 부채 | 영향 | 해소 시점 |
|------|------|----------|
| highlight 파라미터 미구현 | 알림 → 대시보드 해당 지표 강조 불가 | Phase 3 |
| Mock 읽음 처리 로컬 전용 | AlertBell 카운트 Mock 연동 미확인 | 백엔드 연동 시 |
| 알림 실시간 갱신 없음 | 수동 새로고침 또는 refetchOnWindowFocus만 | WebSocket 도입 시 |
| 마감 후 Mock 상태 비영속 | 페이지 새로고침 시 마감 상태 초기화 | 백엔드 연동 시 자동 해소 |
| CloseConfirmDialog 닫기 애니메이션 | BottomSheet 공통 부채 (열기만 slideUp) | BottomSheet 개선 시 |

---

## 14. 후속 작업 연결 (Phase 3 예정)

| 이 PR에서 만든 것 | Phase 3 활용 |
|------------------|-------------|
| AlertCard | 알림 상세 페이지, 인라인 히스토리 |
| OutcomeSelector | 마감 회고 분석 |
| mutations.ts 통합 구조 | Phase 3 mutation 추가 시 확장 |
| severityToStyle | 대시보드 인라인 알림에서 재사용 |
| QUERY_KEYS.alerts 단순화 | Phase 3 알림 필터링 확장 시 키 재설계 가능 |
| CloseConfirmDialog | 다른 위험 작업 확인 다이얼로그 패턴 재사용 |
| BottomSheet common/ | 모든 바텀시트 UI의 단일 소스 |
