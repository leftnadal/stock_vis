# 재무제표 숫자 단위 표시 테스트 케이스

## 테스트 환경

- **대형주**: AAPL (시총 3T, 자산 350B+)
- **중형주**: ROKU (시총 10B, 자산 5B)
- **소형주**: CRSR (시총 500M, 자산 200M)
- **마이크로캡**: GBOX (시총 20M, 자산 5M)

---

## 단위 테스트

### TC-01: 테이블 최대값 계산

**종목**: AAPL
**데이터**:
```json
{
  "total_assets": 352755000000,
  "goodwill": 12750000000,
  "cash": 28975000000
}
```

**테스트**:
```typescript
const maxValue = calculateMaxValue(data);
expect(maxValue).toBe(352755000000);

const unit = getUnitFromMax(maxValue);
expect(unit).toBe('B'); // ≥1B → Billion
```

**예상 결과**:
| 항목 | Auto 모드 (B) | M 모드 | K 모드 |
|------|--------------|--------|--------|
| Total Assets | 352.76 | 352755.00 | 352755000.00 |
| Goodwill | 12.75 | 12750.00 | 12750000.00 |
| Cash | 28.98 | 28975.00 | 28975000.00 |

---

### TC-02: 소형주 Thousand 단위

**종목**: GBOX
**데이터**:
```json
{
  "total_assets": 5234000,
  "cash": 1200000,
  "inventory": 890000
}
```

**테스트**:
```typescript
const maxValue = calculateMaxValue(data);
expect(maxValue).toBe(5234000);

const unit = getUnitFromMax(maxValue);
expect(unit).toBe('M'); // ≥1M → Million
```

**예상 결과**:
| 항목 | Auto 모드 (M) | K 모드 | Raw 모드 |
|------|--------------|--------|----------|
| Total Assets | 5.23 | 5234.00 | 5234000.00 |
| Cash | 1.20 | 1200.00 | 1200000.00 |
| Inventory | 0.89 | 890.00 | 890000.00 |

---

### TC-03: 마이너스 값 처리

**데이터**:
```json
{
  "net_income": -450000000,
  "retained_earnings": -1200000000
}
```

**테스트**:
```typescript
const formatted = formatValue(-450000000, 'M');
expect(formatted).toBe('-450.00');

// 색상 처리
expect(getColorClass(-450000000)).toBe('text-red-600');
```

**예상 결과**:
| 항목 | M 모드 | 색상 |
|------|--------|------|
| Net Income | <span style="color:red">-450.00</span> | 빨강 |
| Retained Earnings | <span style="color:red">-1200.00</span> | 빨강 |

---

## 통합 테스트

### TC-04: 사용자 설정 저장/복원

**시나리오**:
1. AAPL Balance Sheet 열람
2. 단위를 "M"으로 변경
3. 페이지 새로고침
4. 단위가 "M"으로 유지되는지 확인

**테스트**:
```typescript
// 설정 저장
localStorage.setItem('financial-unit-balance-sheet', 'M');

// 페이지 리로드 후
const savedUnit = localStorage.getItem('financial-unit-balance-sheet');
expect(savedUnit).toBe('M');
```

---

### TC-05: 탭별 독립적 설정

**시나리오**:
1. Balance Sheet → "M" 설정
2. Income Statement → "B" 설정
3. Cash Flow → "Auto" 설정
4. 각 탭 전환 시 설정 유지 확인

**테스트**:
```typescript
localStorage.setItem('financial-unit-balance-sheet', 'M');
localStorage.setItem('financial-unit-income-statement', 'B');
localStorage.setItem('financial-unit-cash-flow', 'auto');

// 탭 전환 후
expect(getCurrentUnit('balance-sheet')).toBe('M');
expect(getCurrentUnit('income-statement')).toBe('B');
expect(getCurrentUnit('cash-flow')).toBe('auto');
```

---

## UI 테스트

### TC-06: 단위 버튼 활성화 상태

**예상 UI**:
```
현재 단위: B

[Auto] [B (선택됨)] [M] [K] [원본]
```

**테스트**:
```typescript
render(<FinancialTable data={data} />);

const bButton = screen.getByText('B');
expect(bButton).toHaveClass('bg-blue-600'); // 활성화 상태

const mButton = screen.getByText('M');
expect(mButton).toHaveClass('bg-gray-200'); // 비활성화 상태
```

---

### TC-07: 툴팁 정확한 값 표시

**시나리오**:
- 테이블 셀에 마우스 호버 시 정확한 원본 값 표시

**테스트**:
```typescript
const cell = screen.getByText('352.76'); // 포맷된 값

userEvent.hover(cell);
const tooltip = await screen.findByRole('tooltip');
expect(tooltip).toHaveTextContent('352,755,000,000.00'); // 원본 값
```

---

## 성능 테스트

### TC-08: 대용량 데이터 렌더링

**데이터**: Balance Sheet 100개 필드 × 5년

**테스트**:
```typescript
const startTime = performance.now();

render(<FinancialTable data={largeDataset} />);

const endTime = performance.now();
const renderTime = endTime - startTime;

expect(renderTime).toBeLessThan(100); // 100ms 이하
```

---

### TC-09: 단위 전환 반응성

**테스트**:
```typescript
const { rerender } = render(<FinancialTable unitMode="B" />);

const startTime = performance.now();
rerender(<FinancialTable unitMode="M" />);
const endTime = performance.now();

expect(endTime - startTime).toBeLessThan(50); // 50ms 이하
```

---

## 엣지 케이스

### TC-10: Null/Undefined 값 처리

**데이터**:
```json
{
  "total_assets": 1000000000,
  "goodwill": null,
  "intangible_assets": undefined,
  "cash": 0
}
```

**테스트**:
```typescript
expect(formatValue(null, 'M')).toBe('-');
expect(formatValue(undefined, 'M')).toBe('-');
expect(formatValue(0, 'M')).toBe('0.00');
```

---

### TC-11: 극단적 숫자

**데이터**:
```json
{
  "market_cap": 3000000000000,  // 3T
  "petty_cash": 500              // $500
}
```

**테스트**:
```typescript
// Auto 모드: 최대값(3T) 기준 → B 단위
expect(formatValue(3000000000000, 'B')).toBe('3000.00');
expect(formatValue(500, 'B')).toBe('0.00'); // 반올림 주의

// Raw 모드: 정확한 값 표시
expect(formatValue(500, 'raw')).toBe('500.00');
```

---

## 접근성 테스트

### TC-12: 스크린 리더 호환성

**테스트**:
```typescript
render(<FinancialTable data={data} />);

const cell = screen.getByText('450.25');
expect(cell).toHaveAttribute('aria-label', '450.25 billion dollars');
```

---

### TC-13: 키보드 네비게이션

**테스트**:
```typescript
const autoButton = screen.getByText('Auto');
const bButton = screen.getByText('B');

userEvent.tab(); // Auto 버튼 포커스
expect(autoButton).toHaveFocus();

userEvent.tab(); // B 버튼 포커스
expect(bButton).toHaveFocus();

userEvent.keyboard('{Enter}'); // B 선택
expect(currentUnit).toBe('B');
```

---

## 회귀 테스트

### TC-14: 백엔드 API 응답 변경 없음

**목적**: 프론트엔드 변경이 백엔드에 영향 없음 확인

**테스트**:
```bash
# API 응답 스냅샷 비교
curl http://localhost:8000/api/v1/stocks/api/balance-sheet/AAPL/ > before.json

# 프론트엔드 배포 후
curl http://localhost:8000/api/v1/stocks/api/balance-sheet/AAPL/ > after.json

diff before.json after.json
# Expected: No differences (원본 데이터 동일)
```

---

## 테스트 실행 명령

```bash
# 단위 테스트
npm test -- FinancialTable.test.tsx

# 통합 테스트
npm run test:integration

# E2E 테스트
npx playwright test financial-unit.spec.ts

# 성능 테스트
npm run test:perf

# 접근성 테스트
npm run test:a11y
```

---

## 테스트 커버리지 목표

- **라인 커버리지**: 90% 이상
- **브랜치 커버리지**: 85% 이상
- **함수 커버리지**: 100%

---

## 버그 리포트 양식

발견된 버그는 다음 형식으로 보고:

```markdown
### Bug: [간단한 설명]

**재현 단계**:
1. AAPL 페이지 접속
2. Balance Sheet 탭 클릭
3. "M" 단위 선택
4. 페이지 새로고침

**예상 결과**: 단위 "M" 유지
**실제 결과**: 단위 "Auto"로 복원됨

**환경**:
- 브라우저: Chrome 120
- OS: macOS 14
- 종목: AAPL

**스크린샷**: [첨부]
```
