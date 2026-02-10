# ThesisBuilder Component

## 개요

투자 테제 빌더 컴포넌트 - 스크리너 결과를 AI로 분석하여 투자 테제를 생성하고, Top Picks 및 리스크를 제시합니다.

## Props

```typescript
interface ThesisBuilderProps {
  stocks: ScreenerStock[];        // 현재 스크리너 결과
  filters: ScreenerFilters;        // 적용된 필터
  onThesisGenerated?: (thesis: InvestmentThesis) => void;  // 생성 완료 콜백
  className?: string;
}
```

## 주요 기능

### 1. 2단계 UI

#### 생성 전 상태
- 현재 선별된 종목 수 표시
- 사용자 메모 입력 (선택 사항)
- AI 생성 버튼

#### 생성 후 상태
- 투자 테제 제목 및 요약
- 핵심 지표 뱃지
- Top Picks (클릭 가능한 심볼 링크)
- 리스크 목록
- 공유/저장 버튼

### 2. 주요 액션

| 버튼 | 기능 | 상태 |
|------|------|------|
| **생성하기** | AI로 투자 테제 생성 | ✅ 구현 완료 |
| **공유** | share_code 생성 → 링크 복사 | ✅ 구현 완료 |
| **저장** | Watchlist에 Top Picks 추가 | ⏳ 추후 구현 |
| **새로 생성** | 폼 초기화 | ✅ 구현 완료 |

## 사용법

### 기본 사용

```tsx
import { ThesisBuilder } from '@/components/screener';

function ScreenerPage() {
  const [stocks, setStocks] = useState<ScreenerStock[]>([]);
  const [filters, setFilters] = useState<ScreenerFilters>({});

  return (
    <ThesisBuilder
      stocks={stocks}
      filters={filters}
      onThesisGenerated={(thesis) => {
        console.log('Generated thesis:', thesis);
      }}
    />
  );
}
```

### 콜백 활용

```tsx
<ThesisBuilder
  stocks={filteredStocks}
  filters={appliedFilters}
  onThesisGenerated={(thesis) => {
    // 생성 완료 후 동작
    toast.success('투자 테제가 생성되었습니다!');

    // 추가 처리 (예: 분석 대시보드로 이동)
    router.push(`/thesis/${thesis.id}`);
  }}
/>
```

## API 연동

### 엔드포인트

```bash
POST /api/v1/serverless/thesis/generate
Body:
{
  "stocks": [{ symbol, company_name, sector, ... }],
  "filters": { per_max: 25, roe_min: 15, ... },
  "user_notes": "저평가 고배당 성장주 중심 포트폴리오"
}

Response:
{
  "success": true,
  "data": {
    "id": 123,
    "title": "저평가 고배당 성장주",
    "summary": "배당수익률 3% 이상 + ROE 15% 이상인 종목들로...",
    "key_metrics": ["배당수익률 ≥ 3%", "ROE ≥ 15%", "PER < 25"],
    "top_picks": ["AAPL", "MSFT", "JNJ", "PG", "KO"],
    "risks": ["금리 인상 시 배당주 매력 감소", "성장주 대비 자본차익 제한적"],
    "share_code": "abc123xyz",
    "created_at": "2026-01-30T12:00:00Z"
  }
}
```

### screenerService 메서드

```typescript
// 투자 테제 생성
await screenerService.generateThesis(stocks, filters, userNotes);

// 내 테제 목록 조회
await screenerService.getMyTheses();

// 특정 테제 조회
await screenerService.getThesis(thesisId);
```

## UI 상태

### 로딩 상태
```tsx
<button disabled={isGenerating}>
  <Loader2 className="animate-spin" />
  AI로 분석 중...
</button>
```

### 에러 상태
```tsx
{error && (
  <div className="border-[#F85149]/30 bg-[#F85149]/10">
    <AlertCircle />
    {error}
  </div>
)}
```

### 빈 상태
```tsx
{stocks.length === 0 && (
  <p>필터링된 종목이 없습니다. 필터를 조정해주세요.</p>
)}
```

## 스타일링

### 다크 테마
- 배경: `bg-[#161B22]`
- 테두리: `border-[#30363D]`
- 텍스트 (primary): `text-[#E6EDF3]`
- 텍스트 (secondary): `text-[#8B949E]`
- 액센트: `text-[#58A6FF]`

### 컴포넌트 구조
```
┌─ ThesisBuilder ─────────────────────────────────────┐
│  [Header]                                           │
│  💡 투자 테제 빌더                                   │
├─────────────────────────────────────────────────────┤
│  [Content]                                          │
│  • 생성 전: Form (메모 입력 + 버튼)                  │
│  • 생성 후: Thesis Card (제목, 요약, 지표, TOP, 리스크)│
└─────────────────────────────────────────────────────┘
```

## 예시 응답

### 투자 테제 객체

```typescript
{
  id: 123,
  title: "저평가 고배당 성장주",
  summary: "배당수익률 3% 이상 + ROE 15% 이상인 종목들로 구성된 포트폴리오. 안정적인 배당 수익과 함께 기업 성장성을 동시에 추구하는 전략입니다.",
  key_metrics: [
    "배당수익률 ≥ 3%",
    "ROE ≥ 15%",
    "PER < 25"
  ],
  top_picks: ["AAPL", "MSFT", "JNJ", "PG", "KO"],
  risks: [
    "금리 인상 시 배당주 매력 감소",
    "성장주 대비 자본차익 제한적",
    "경기침체 시 배당 삭감 리스크"
  ],
  share_code: "abc123xyz",
  created_at: "2026-01-30T12:00:00Z"
}
```

## Phase 2.3 체크리스트

- [x] InvestmentThesis 타입 정의 (types/screener.ts)
- [x] screenerService API 메서드 추가
- [x] ThesisBuilder 컴포넌트 생성
- [x] 2단계 UI (생성 전/후)
- [x] 공유 기능 (share_code → 링크 복사)
- [x] 로딩/에러/빈 상태 처리
- [ ] 백엔드 API 구현 (serverless/views.py)
- [ ] Watchlist 저장 기능 (추후)

## 다음 단계

1. **백엔드 구현** (`@backend`)
   - `POST /api/v1/serverless/thesis/generate` 엔드포인트
   - LLM 기반 투자 테제 생성 로직
   - share_code 생성 및 저장

2. **통합 테스트** (`@qa-architect`)
   - 스크리너 페이지에 ThesisBuilder 통합
   - 다양한 필터 조합 테스트
   - 에러 케이스 검증

3. **UX 개선** (`@investment-advisor`)
   - 투자 테제 품질 검토
   - 리스크 항목 충실도 확인

## 관련 컴포넌트

- **ChainSightPanel**: 연관 종목 추천
- **PresetGallery**: 프리셋 갤러리
- **SharePresetModal**: 프리셋 공유 모달 (참고 패턴)

## 기술적 고려사항

### TypeScript strict mode
- 모든 props 타입 정의 완료
- optional 체이닝 사용 (`thesis?.share_code`)
- null 체크 완료

### 상태 관리
- 로컬 상태: `useState` 사용
- 서버 상태: TanStack Query 권장 (추후 개선)

### 에러 핸들링
```typescript
try {
  const response = await screenerService.generateThesis(...);
  if (response.success) {
    setThesis(response.data);
  } else {
    setError('투자 테제 생성에 실패했습니다.');
  }
} catch (err) {
  setError('투자 테제 생성 중 오류가 발생했습니다.');
}
```

## 참고

- Phase 2.3 설계 문서: `docs/SCREENER_UPGRADE_PLAN.md`
- 타입 정의: `frontend/types/screener.ts`
- 서비스: `frontend/services/screenerService.ts`
