# 재무제표 숫자 단위 표시 최종 확정 사양

**문서 버전**: 1.0
**최종 확정일**: 2025-11-28
**검토자**: @qa (4개 에이전트 의견 종합)

---

## 1. 의사결정 요약

### 핵심 결정사항

| 쟁점 | 최종 결정 | 근거 |
|-----|---------|------|
| 단위 결정 위치 | **프론트엔드** | 캐시 효율, RESTful 원칙, 확장성 |
| 단위 결정 기준 | **테이블 최대값 기준 통일** + 사용자 전환 | 행간 비교 용이, Bloomberg 방식 |
| 임계값 | **절대값 기준** (1B, 1M, 1K) | 직관성, 재무제표 항목과 무관 |
| 백엔드 수정 | **불필요** | 현재 `fields = '__all__'` 유지 |
| 구현 우선순위 | **Phase 1 → Phase 2 → Phase 3** | 점진적 개선 |

### 에이전트별 의견 반영도

- **@investment-advisor**: ⭐⭐⭐⭐ (Bloomberg 방식 + Auto 모드 채택)
- **@backend**: ⭐⭐ (백엔드 수정 불필요 결정으로 일부 반영 안 됨)
- **@frontend**: ⭐⭐⭐⭐⭐ (핵심 아이디어 전면 채택)
- **@infra**: ⭐⭐⭐⭐⭐ (캐시 전략 100% 채택)

---

## 2. 기술 사양

### 2.1 데이터 플로우

```
┌─────────────────────────────────────────────────────────────┐
│                    Django Backend                           │
│  stocks/views.py: StockBalanceSheetAPIView                  │
│  - 원본 숫자 그대로 반환 (fields = '__all__')              │
│  - Redis 캐싱: 1시간 (재무제표 업데이트 주기)              │
└─────────────────────┬───────────────────────────────────────┘
                      │ JSON 응답
                      ▼
          {
            "total_assets": 352755000000.00,
            "goodwill": 12750000000.00,
            ...
          }
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Next.js Frontend (TypeScript)                  │
│  components/stock/FinancialTable.tsx (신규)                 │
│                                                             │
│  1. 테이블 데이터 수신                                      │
│  2. 최대값 계산: Math.max(...values)                        │
│  3. 단위 결정:                                              │
│     - Auto 모드: maxValue >= 1B → 'B'                       │
│     - 수동 모드: 사용자 선택 ('B', 'M', 'K', 'raw')         │
│  4. 숫자 포맷팅: value / divisor                            │
│  5. 렌더링: <td>{formatted}</td>                            │
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼
          사용자 설정 → localStorage
          'financial-unit-balance-sheet': 'M'
```

---

### 2.2 단위 결정 로직

#### 알고리즘 의사코드

```typescript
// Step 1: 테이블 내 최대값 계산
function calculateMaxValue(data: FinancialData[]): number {
  let max = 0;
  data.forEach(row => {
    Object.entries(row).forEach(([key, value]) => {
      if (typeof value === 'number' && !isDateField(key)) {
        max = Math.max(max, Math.abs(value));
      }
    });
  });
  return max;
}

// Step 2: 단위 결정
function determineUnit(maxValue: number, userMode: UnitMode): Unit {
  if (userMode !== 'auto') {
    return userMode; // 사용자 수동 선택 우선
  }

  // Auto 모드: 절대값 기준
  if (maxValue >= 1e9) return 'B';  // Billion
  if (maxValue >= 1e6) return 'M';  // Million
  if (maxValue >= 1e3) return 'K';  // Thousand
  return 'raw';                      // 원본
}

// Step 3: 숫자 포맷팅
function formatValue(value: number, unit: Unit): string {
  const divisors = {
    'B': 1e9,
    'M': 1e6,
    'K': 1e3,
    'raw': 1,
  };

  const formatted = (value / divisors[unit]).toFixed(2);
  return value < 0 ? formatted : formatted; // 마이너스 부호 유지
}
```

---

### 2.3 컴포넌트 구조

```typescript
// frontend/components/stock/FinancialTable.tsx

import { useState, useEffect, useMemo } from 'react';

export type UnitMode = 'auto' | 'B' | 'M' | 'K' | 'raw';
export type FinancialType = 'balance-sheet' | 'income-statement' | 'cash-flow';

interface FinancialTableProps {
  data: any[];
  type: FinancialType;
  symbol: string; // Phase 3에서 종목별 설정 저장용
}

export default function FinancialTable({ data, type, symbol }: FinancialTableProps) {
  // State
  const [unitMode, setUnitMode] = useState<UnitMode>('auto');

  // localStorage 연동
  useEffect(() => {
    const savedUnit = localStorage.getItem(`financial-unit-${type}`);
    if (savedUnit) setUnitMode(savedUnit as UnitMode);
  }, [type]);

  // 최대값 계산 (memoization)
  const maxValue = useMemo(() => calculateMaxValue(data), [data]);

  // 현재 단위 결정
  const currentUnit = useMemo(() =>
    determineUnit(maxValue, unitMode),
    [maxValue, unitMode]
  );

  // 단위 변경 핸들러
  const handleUnitChange = (newMode: UnitMode) => {
    setUnitMode(newMode);
    localStorage.setItem(`financial-unit-${type}`, newMode);
  };

  return (
    <div>
      {/* 단위 선택 UI */}
      <UnitSelector
        currentMode={unitMode}
        currentUnit={currentUnit}
        onChange={handleUnitChange}
      />

      {/* 재무제표 테이블 */}
      <table className="financial-table">
        <thead>
          <tr>
            <th>항목</th>
            {data.map((item, idx) => (
              <th key={idx}>
                {formatDate(item.fiscal_date_ending)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {getFinancialFields(type).map(field => (
            <FinancialRow
              key={field.key}
              label={field.label}
              data={data}
              fieldKey={field.key}
              unit={currentUnit}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

// 단위 선택 컴포넌트
function UnitSelector({ currentMode, currentUnit, onChange }: UnitSelectorProps) {
  const modes: UnitMode[] = ['auto', 'B', 'M', 'K', 'raw'];

  return (
    <div className="flex justify-between items-center mb-4">
      {/* 현재 단위 표시 */}
      <div className="text-sm text-gray-600">
        단위: <span className="font-semibold">{getUnitLabel(currentUnit)}</span>
      </div>

      {/* 단위 버튼 그룹 */}
      <div className="flex space-x-2" role="group" aria-label="숫자 단위 선택">
        {modes.map(mode => (
          <button
            key={mode}
            onClick={() => onChange(mode)}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
              currentMode === mode
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
            aria-pressed={currentMode === mode}
          >
            {getUnitLabel(mode)}
          </button>
        ))}
      </div>
    </div>
  );
}

// 재무제표 행 컴포넌트
function FinancialRow({ label, data, fieldKey, unit }: FinancialRowProps) {
  return (
    <tr className="border-b dark:border-gray-700">
      <td className="py-2 px-4 text-sm text-gray-600 font-medium">
        {label}
      </td>
      {data.map((item, idx) => {
        const value = item[fieldKey];
        const formatted = formatValue(value, unit);

        return (
          <td
            key={idx}
            className={`text-right py-2 px-4 text-sm ${getColorClass(value)}`}
            title={value?.toLocaleString('en-US', { maximumFractionDigits: 2 }) || '-'}
          >
            {formatted}
          </td>
        );
      })}
    </tr>
  );
}

// 유틸리티 함수
function getUnitLabel(unit: UnitMode | Unit): string {
  const labels = {
    'auto': 'Auto',
    'B': 'Billion',
    'M': 'Million',
    'K': 'Thousand',
    'raw': '원본',
  };
  return labels[unit];
}

function getColorClass(value: number | null | undefined): string {
  if (value === null || value === undefined) return 'text-gray-400';
  return value < 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-900 dark:text-white';
}

function getFinancialFields(type: FinancialType): FieldConfig[] {
  // type별로 표시할 필드 정의
  const fields = {
    'balance-sheet': [
      { key: 'total_assets', label: 'Total Assets' },
      { key: 'total_current_assets', label: 'Current Assets' },
      { key: 'cash_and_cash_equivalents', label: 'Cash & Equivalents' },
      { key: 'inventory', label: 'Inventory' },
      { key: 'total_liabilities', label: 'Total Liabilities' },
      { key: 'total_shareholder_equity', label: 'Shareholder Equity' },
      // ... 더 많은 필드
    ],
    'income-statement': [
      { key: 'total_revenue', label: 'Total Revenue' },
      { key: 'gross_profit', label: 'Gross Profit' },
      { key: 'operating_income', label: 'Operating Income' },
      { key: 'net_income', label: 'Net Income' },
      // ...
    ],
    'cash-flow': [
      { key: 'operating_cashflow', label: 'Operating Cash Flow' },
      { key: 'cashflow_from_investment', label: 'Investing Cash Flow' },
      { key: 'cashflow_from_financing', label: 'Financing Cash Flow' },
      // ...
    ],
  };

  return fields[type];
}
```

---

### 2.4 기존 코드 수정 위치

#### `frontend/app/stocks/[symbol]/page.tsx`

**수정 전** (Line 386-426):
```typescript
{/* Financial Data Table */}
{data.length > 0 ? (
  <div className="overflow-x-auto">
    <table className="min-w-full">
      <tbody>
        {Object.keys(data[0])
          .filter(...)
          .map((key) => (
            <td>
              {typeof item[key] === 'number'
                ? new Intl.NumberFormat('en-US', {
                    notation: 'compact',
                    maximumFractionDigits: 1
                  }).format(item[key])  // ❌ 행별 동적 단위 (문제 발생)
                : item[key] || '-'}
            </td>
          ))}
      </tbody>
    </table>
  </div>
) : (...)}
```

**수정 후**:
```typescript
{/* Financial Data Table */}
{data.length > 0 ? (
  <FinancialTable
    data={data}
    type={type}
    symbol={symbol}
  />
) : (
  <p className="text-center text-gray-500 py-8">데이터가 없습니다.</p>
)}
```

**변경 이유**:
- 기존: `notation: 'compact'`로 행별 동적 단위 (450.3B, 12.5M 혼재)
- 신규: `FinancialTable` 컴포넌트로 테이블 통일 단위 적용

---

## 3. 구현 단계별 계획

### Phase 1: 기본 구현 (1주일)

**목표**: 현재 문제점 해결

**작업 항목**:
- [ ] `FinancialTable.tsx` 컴포넌트 신규 생성
- [ ] `calculateMaxValue()` 함수 구현
- [ ] `determineUnit()` 로직 구현
- [ ] `formatValue()` 포맷팅 함수
- [ ] `UnitSelector` UI 컴포넌트
- [ ] localStorage 연동
- [ ] 기존 페이지에서 호출

**테스트**:
- TC-01 ~ TC-05 (단위 테스트, 통합 테스트)

**예상 결과**:
- ✅ 테이블 내 모든 숫자가 같은 단위로 표시
- ✅ Auto/B/M/K/원본 버튼으로 수동 전환 가능
- ✅ 사용자 설정이 localStorage에 저장/복원

---

### Phase 2: 고급 기능 (2주일)

**목표**: UX 개선 및 전문성 강화

**작업 항목**:
- [ ] 행별 동적 모드 추가 (Bloomberg Auto 모드)
  ```typescript
  type AutoMode = 'table-max' | 'row-dynamic';
  ```
- [ ] 툴팁으로 정확한 원본 값 표시
- [ ] CSV 다운로드 기능 (선택된 단위로)
- [ ] 키보드 단축키 (U: Unit toggle)
- [ ] 마이너스 값 색상 강조 개선

**테스트**:
- TC-06 ~ TC-09 (UI, 성능 테스트)

**예상 결과**:
- ✅ 사용자가 "Row Dynamic" 모드 선택 가능
- ✅ 마우스 호버 시 "352,755,000,000.00" 표시
- ✅ CSV 내보내기 시 단위 헤더 포함

---

### Phase 3: 프로페셔널 기능 (1개월)

**목표**: 금융 전문가를 위한 고급 기능

**작업 항목**:
- [ ] 종목별 설정 기억
  ```typescript
  localStorage.setItem(`financial-unit-${symbol}-${type}`, mode);
  ```
- [ ] 비율 계산 도구 내장
  - Debt/Equity Ratio 자동 계산
  - Quick Ratio 시각화
- [ ] 시계열 차트 연동
  - 재무제표 값 클릭 → 5년 트렌드 차트
- [ ] 다크 모드 최적화
- [ ] 프린트 최적화 (단위 헤더 포함)

**테스트**:
- TC-10 ~ TC-13 (엣지 케이스, 접근성)

**예상 결과**:
- ✅ AAPL은 "B", GBOX는 "M" 기억
- ✅ Debt/Equity 비율 자동 계산 및 색상 코딩
- ✅ Net Income 클릭 → 5년 차트 팝업

---

## 4. 성능 및 최적화

### 4.1 성능 목표

| 지표 | 목표 | 측정 방법 |
|-----|------|----------|
| 초기 렌더링 | < 100ms | `performance.now()` |
| 단위 전환 | < 50ms | React DevTools Profiler |
| 메모리 사용 | < 5MB 증가 | Chrome Memory Profiler |
| 번들 크기 | < 10KB 추가 | `npm run build --analyze` |

### 4.2 최적화 전략

**1. Memoization**:
```typescript
const maxValue = useMemo(() => calculateMaxValue(data), [data]);
const currentUnit = useMemo(() => determineUnit(maxValue, unitMode), [maxValue, unitMode]);
```

**2. 가상 스크롤 (대량 데이터)**:
```typescript
import { FixedSizeList } from 'react-window';

// 100개 이상 행 시 가상 스크롤 적용
{rows.length > 100 ? (
  <FixedSizeList height={600} itemCount={rows.length} itemSize={35}>
    {({ index, style }) => <FinancialRow style={style} {...rows[index]} />}
  </FixedSizeList>
) : (
  rows.map(row => <FinancialRow {...row} />)
)}
```

**3. Code Splitting**:
```typescript
const FinancialTable = dynamic(() => import('@/components/stock/FinancialTable'), {
  loading: () => <TableSkeleton />,
  ssr: true,
});
```

---

## 5. 품질 보증

### 5.1 코드 리뷰 체크리스트

**@qa 검토 항목**:
- [ ] TypeScript strict mode 위반 없음
- [ ] `any` 타입 사용 없음 (Props, State 모두 타입 정의)
- [ ] 모든 숫자는 `number | null | undefined` 처리
- [ ] 접근성: `aria-label`, `aria-pressed` 속성 포함
- [ ] 다크 모드 지원: `dark:` 클래스 적용
- [ ] 에러 바운더리 추가

**@frontend 검토 항목**:
- [ ] 컴포넌트 재사용성: `FinancialTable`이 3개 탭에서 공통 사용
- [ ] Props 네이밍: `symbol`, `type`, `data` 명확함
- [ ] 상태 관리: `useState` + `localStorage` 동기화
- [ ] 성능: `useMemo`, `useCallback` 적절히 사용

**@infra 검토 항목**:
- [ ] 백엔드 API 변경 없음 (캐시 무효화 불필요)
- [ ] localStorage 용량 고려 (key당 최대 5KB 이하)
- [ ] CDN 캐싱 호환성: 동적 단위는 클라이언트 처리

---

### 5.2 테스트 커버리지

**목표**:
- 라인 커버리지: 90% 이상
- 브랜치 커버리지: 85% 이상
- 함수 커버리지: 100%

**실행 명령**:
```bash
npm test -- --coverage FinancialTable.test.tsx
```

**예상 결과**:
```
File                     | % Stmts | % Branch | % Funcs | % Lines |
-------------------------|---------|----------|---------|---------|
FinancialTable.tsx       |   92.5  |   87.3   |  100.0  |   93.1  |
  calculateMaxValue      |  100.0  |  100.0   |  100.0  |  100.0  |
  determineUnit          |  100.0  |   90.0   |  100.0  |  100.0  |
  formatValue            |   95.0  |   85.0   |  100.0  |   96.0  |
  UnitSelector           |   88.0  |   82.0   |  100.0  |   89.0  |
```

---

## 6. 배포 전 체크리스트

### 6.1 기능 테스트

- [ ] AAPL (대형주): Total Assets 352B 올바르게 표시
- [ ] GBOX (마이크로캡): Cash 1.2M 올바르게 표시
- [ ] 단위 전환: Auto → B → M → K → 원본 모두 정상 작동
- [ ] localStorage: 페이지 새로고침 시 설정 유지
- [ ] 탭 전환: Balance Sheet (M) ↔ Income Statement (B) 독립적 설정

### 6.2 크로스 브라우저 테스트

- [ ] Chrome 120+ (Windows, macOS)
- [ ] Firefox 121+
- [ ] Safari 17+ (macOS, iOS)
- [ ] Edge 120+

### 6.3 접근성 테스트

- [ ] 스크린 리더: NVDA, VoiceOver 호환
- [ ] 키보드 네비게이션: Tab, Enter, Space
- [ ] 색상 대비: WCAG AA 준수 (4.5:1 이상)

### 6.4 성능 테스트

- [ ] Lighthouse 점수: Performance 90+ 유지
- [ ] First Contentful Paint: < 1.5s
- [ ] Cumulative Layout Shift: < 0.1

---

## 7. 문서화

### 7.1 사용자 가이드

**위치**: `docs/user-guide-financial-unit.md`

**내용**:
- 단위 선택 UI 사용법
- Auto 모드 설명
- 툴팁으로 정확한 값 확인하기
- CSV 다운로드 방법 (Phase 2)

### 7.2 개발자 문서

**위치**: `docs/dev-guide-financial-unit.md`

**내용**:
- 컴포넌트 API 문서
- 새로운 재무제표 타입 추가 방법
- 단위 포맷팅 커스터마이징

### 7.3 API 문서

**위치**: `docs/api-financial-data.md`

**내용**:
```yaml
GET /api/v1/stocks/api/balance-sheet/<symbol>/
Response:
  {
    "symbol": "AAPL",
    "tab": "balance_sheet",
    "period": "annual",
    "data": [
      {
        "fiscal_date_ending": "2023-09-30",
        "total_assets": 352755000000.00,  # 원본 숫자 (프론트에서 단위 결정)
        "goodwill": 12750000000.00,
        ...
      }
    ]
  }

Note:
- 모든 숫자는 원본 값 그대로 반환 (단위 없음)
- 프론트엔드에서 사용자 선호도에 따라 단위 적용
- 백엔드는 캐싱만 담당 (1시간 TTL)
```

---

## 8. 향후 개선 사항

### 8.1 Phase 4: AI 분석 통합 (3개월 후)

**LLM 활용**:
- "Total Assets가 급증했습니다 (전년 대비 +25%)" 자동 분석
- 재무비율 이상치 탐지 및 알림
- 경쟁사 비교 테이블 자동 생성

**@rag-llm 협업 필요**:
- 재무제표 데이터를 RAG 임베딩
- 사용자 질문: "AAPL의 부채비율이 위험한가요?"
- LLM 응답: "2023년 부채비율 35%로 업계 평균 50% 대비 안전합니다."

### 8.2 Phase 5: 모바일 최적화

- 가로 스크롤 제거 (카드형 레이아웃)
- Pinch-to-zoom 지원
- 오프라인 모드 (Service Worker)

---

## 9. 리스크 관리

### 9.1 잠재적 이슈

| 리스크 | 확률 | 영향도 | 완화 전략 |
|-------|------|--------|----------|
| localStorage 용량 초과 | 낮음 | 중 | 설정 압축, 오래된 데이터 정리 |
| 브라우저 호환성 문제 | 중 | 중 | Polyfill 추가, 크로스 브라우저 테스트 |
| 성능 저하 (대량 데이터) | 중 | 높음 | 가상 스크롤, 페이지네이션 |
| 사용자 혼란 (단위 변경) | 높음 | 낮음 | 툴팁, 사용자 가이드 |

### 9.2 롤백 계획

**문제 발생 시 조치**:
1. 즉시 이전 버전으로 롤백 (Git revert)
2. 기존 `notation: 'compact'` 방식 복원
3. 버그 수정 후 재배포

**롤백 조건**:
- 크리티컬 버그 (데이터 손실, 심각한 성능 저하)
- 사용자 컴플레인 급증 (하루 10건 이상)
- 테스트 커버리지 80% 미만

---

## 10. 승인 및 서명

**문서 작성**: @qa (Claude Code)
**검토 완료**:
- [ ] @investment-advisor: 투자 도메인 관점 확인
- [ ] @backend: 백엔드 영향도 확인 (수정 불필요 확인됨)
- [ ] @frontend: 구현 가능성 확인
- [ ] @infra: 인프라 영향도 확인 (캐시 전략 승인)

**최종 승인**: [사용자 확인 필요]

**배포 예정일**: Phase 1 구현 완료 후 (약 1주일 후)

---

## 부록

### A. 용어 사전

- **Auto 모드**: 테이블 내 최대값을 기준으로 자동으로 단위를 결정하는 모드
- **Row Dynamic**: 각 행마다 다른 단위를 적용하는 Bloomberg 방식 (Phase 2)
- **Raw 모드**: 원본 숫자를 그대로 표시 (450256000000.00)
- **임계값**: 단위를 결정하는 기준 값 (1B, 1M, 1K)

### B. 참고 자료

- [Bloomberg Terminal UI 가이드](https://www.bloomberg.com/professional/support/documentation/)
- [Yahoo Finance 재무제표 예시](https://finance.yahoo.com/quote/AAPL/balance-sheet)
- [Intl.NumberFormat 브라우저 호환성](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/NumberFormat)

### C. 변경 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|-----|------|----------|--------|
| 1.0 | 2025-11-28 | 최초 작성 (4개 에이전트 의견 종합) | @qa |
