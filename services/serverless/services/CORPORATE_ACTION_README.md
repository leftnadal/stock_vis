# Corporate Action 감지 시스템

## 개요

가격 변동 ±50% 이상 시 주식분할, 역분할, 배당 등의 기업 이벤트를 자동 감지하는 시스템입니다.

## 주요 기능

### 1. 자동 감지
- **트리거 조건**: 가격 변동 ±50% 이상
- **데이터 소스**: yfinance API (무료)
- **감지 대상**:
  - 주식분할 (Stock Split)
  - 역주식분할 (Reverse Split)
  - 특별배당 (Special Dividend)

### 2. 데이터 모델

#### CorporateAction
```python
{
    "symbol": "GRI",
    "date": "2024-01-12",
    "action_type": "reverse_split",  # split, reverse_split, dividend
    "ratio": 0.0357,                 # 분할 비율
    "dividend_amount": null,
    "display_text": "28:1 역분할",
    "source": "yfinance"
}
```

#### MarketMover 필드 추가
```python
{
    "has_corporate_action": true,
    "corporate_action_type": "reverse_split",
    "corporate_action_display": "28:1 역분할"
}
```

## 사용법

### 1. Service 직접 사용
```python
from serverless.services.corporate_action_service import CorporateActionService
from datetime import date

service = CorporateActionService()

# 1. 체크 필요 여부 확인
change_percent = 2772.0  # GRI Bio 역분할 사례
if service.should_check(change_percent):
    # 2. Corporate Action 감지
    action = service.check_actions('GRI', date(2024, 1, 15))

    if action:
        # 3. DB 저장
        saved = service.save_action('GRI', action)
        print(saved.display_text)  # "28:1 역분할"
```

### 2. MarketMoversSync 통합 (자동)
```python
# serverless/services/data_sync.py
# _process_item() 메서드에서 자동 호출됨

# 변동률 ±50% 이상인 종목에 대해 자동 감지
if self.action_service.should_check(change_percent):
    corporate_action = self.action_service.check_actions(symbol, date)
    if corporate_action:
        # MarketMover에 정보 저장
        has_corporate_action = True
        corporate_action_type = corporate_action['action_type']
        corporate_action_display = corporate_action['display_text']
```

## 감지 로직

### 1. 주식분할/역분할

**yfinance ratio 규칙**:
- `ratio > 1`: 정분할 (예: 4.0 → 1주가 4주로 분할)
- `ratio < 1`: 역분할 (예: 0.0357 → 28주가 1주로 통합)

**예시**:
```python
# AAPL 4:1 정분할 (2020-08-31)
ticker.splits
# 2020-08-31    4.0

# GRI 28:1 역분할 (2024-01-12)
ticker.splits
# 2024-01-12    0.035714  # 1/28
```

### 2. 특별배당

**감지 조건**:
- 배당 수익률 5% 이상
- 계산식: `(배당금 / 현재주가) * 100 >= 5.0`

**예시**:
```python
# $5 배당, 주가 $90
dividend_yield = (5.0 / 90.0) * 100  # 5.55%
# → "특별배당 $5.00 (5.5%)"
```

### 3. LOOKBACK_DAYS

- 기본값: 7일
- 대상 날짜 ±7일 이내의 이벤트만 감지
- 예: 2026-01-20 기준 → 2026-01-13 ~ 2026-01-21 범위

## API 응답 예시

### Market Movers API
```bash
GET /api/v1/serverless/movers?type=gainers&date=2024-01-15
```

```json
{
  "success": true,
  "data": [
    {
      "rank": 1,
      "symbol": "GRI",
      "company_name": "GRI Bio",
      "change_percent": "2772.00",
      "has_corporate_action": true,
      "corporate_action_type": "reverse_split",
      "corporate_action_display": "28:1 역분할"
    }
  ]
}
```

## 테스트

### 1. 유닛 테스트 (12개)
```bash
pytest tests/serverless/test_corporate_action_service.py -v
```

**테스트 커버리지**:
- ✅ should_check() 임계값 테스트
- ✅ 정분할 감지 (ratio > 1)
- ✅ 역분할 감지 (ratio < 1)
- ✅ 특별배당 감지 (5% 이상)
- ✅ LOOKBACK_DAYS 범위 체크
- ✅ yfinance 없을 때 폴백
- ✅ DB 저장 테스트

### 2. 통합 테스트
```bash
python scripts/test_corporate_action_detection.py
```

**실제 사례**:
- GRI Bio: 28:1 역분할 (2024-01-12)
- AAPL: 4:1 정분할 (2020-08-31)
- MSFT: Corporate Action 없음 (정상)

## 에러 핸들링

### 1. yfinance 없을 때
```python
# CorporateActionService.__init__()
try:
    import yfinance as yf
    self._available = True
except ImportError:
    logger.warning("yfinance not installed")
    self._available = False
```

### 2. API 호출 실패
```python
# check_actions()
try:
    ticker = self.yf.Ticker(symbol)
    # ... 감지 로직
except Exception as e:
    logger.warning(f"Corporate Action 체크 실패: {e}")
    return None  # 메인 플로우 중단 안 함
```

### 3. 데이터 품질 문제
```python
# _check_splits()
if splits is None or len(splits) == 0:
    return None  # 분할 이력 없음

# _check_dividends()
if current_price is None or current_price <= 0:
    continue  # 가격 데이터 없음
```

## 주의사항

### 1. yfinance pandas Series
```python
# ❌ 잘못된 방법
for split_date in ticker.splits:
    date_obj = split_date.date()  # AttributeError!

# ✅ 올바른 방법
for split_timestamp, ratio in ticker.splits.items():
    date_obj = split_timestamp.date()
```

### 2. ratio 해석
```python
# yfinance ratio는 "1주당 몇 주로 분할되는가"
# ratio > 1: 정분할 (1 → N)
# ratio < 1: 역분할 (N → 1)

# 예시
ratio = 4.0        # 1:4 정분할
ratio = 0.0357     # 28:1 역분할 (1/28)
```

### 3. 메인 플로우 중단 방지
```python
# data_sync.py
try:
    action = self.action_service.check_actions(symbol, date)
    if action:
        self.action_service.save_action(symbol, action)
except Exception as e:
    logger.warning(f"Corporate Action 감지 실패: {e}")
    # 에러 무시, 메인 동기화 계속 진행
```

## 마이그레이션

```bash
# 마이그레이션 생성 (완료)
python manage.py makemigrations serverless --name add_corporate_action_fields

# 마이그레이션 적용
python manage.py migrate serverless
```

## 향후 개선 사항

### 1. 프론트엔드 표시
- Badge 컴포넌트: "28:1 역분할" 뱃지 표시
- Tooltip: 상세 정보 (날짜, 비율 등)

### 2. 알림 시스템
- 사용자 Watchlist 종목에 Corporate Action 발생 시 알림
- Email/Push 알림 (optional)

### 3. 히스토리 조회
- `/api/v1/serverless/corporate-actions/<symbol>/` 엔드포인트
- 종목별 Corporate Action 이력 조회

## 참고 문서

- **CLAUDE.md**: Corporate Action 감지 시스템 섹션
- **자주 발생하는 버그 #13**: yfinance pandas Series 타입 불일치
- **외부 API**: yfinance (Yahoo Finance) 섹션
