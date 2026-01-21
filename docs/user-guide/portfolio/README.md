# Portfolio (포트폴리오)

> 개인 투자 포트폴리오 관리 및 성과 추적

## 📋 상태

**개발 중 (In Progress)**

이 페이지는 현재 개발 진행 중입니다. 완성되면 다음 내용이 포함될 예정입니다:

- 포트폴리오 생성 및 관리
- 보유 종목 추가/수정/삭제
- 실시간 평가액 및 수익률 계산
- 섹터/자산 배분 시각화
- 배당금 추적
- 거래 내역 관리

---

## 현재 구현된 기능

### Watchlist (관심종목)

포트폴리오의 일부 기능인 Watchlist가 구현되어 있습니다.

- **기능**:
  - 관심종목 리스트 생성/수정/삭제
  - 종목 추가/제거
  - 목표 진입가 설정
  - 메모 작성
  - 실시간 가격 조회

- **API 엔드포인트**:
  ```bash
  GET    /api/v1/users/watchlist/              # 리스트 목록
  POST   /api/v1/users/watchlist/              # 리스트 생성
  GET    /api/v1/users/watchlist/<id>/         # 리스트 상세
  PATCH  /api/v1/users/watchlist/<id>/         # 리스트 수정
  DELETE /api/v1/users/watchlist/<id>/         # 리스트 삭제
  POST   /api/v1/users/watchlist/<id>/add-stock/    # 종목 추가
  GET    /api/v1/users/watchlist/<id>/stocks/      # 종목 목록
  ```

- **코드 위치**:
  - Backend Model: `users/models.py` - `Watchlist`, `WatchlistItem`
  - Backend View: `users/views.py`
  - Frontend: `frontend/app/portfolio/` (예정)

---

## 데이터베이스 스키마

### users 앱

**User**
```python
class User(AbstractUser):
    # Django 기본 User 모델 확장
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Watchlist**
```python
class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlists')
    name = models.CharField(max_length=100)  # "Tech Stocks", "Value Plays" 등
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['user', 'name']]
        ordering = ['-is_default', '-created_at']
```

**WatchlistItem**
```python
class WatchlistItem(models.Model):
    watchlist = models.ForeignKey(Watchlist, on_delete=models.CASCADE, related_name='items')
    stock = models.ForeignKey('stocks.Stock', on_delete=models.CASCADE)

    # 투자 관리 필드
    target_entry_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="목표 진입가"
    )
    notes = models.TextField(
        blank=True,
        help_text="투자 메모 (매수 이유, 전략 등)"
    )
    position_order = models.IntegerField(
        default=0,
        help_text="리스트 내 정렬 순서"
    )

    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['watchlist', 'stock']]
        ordering = ['position_order', '-added_at']
```

### 모델 관계

```
User (1) ──────── (N) Watchlist
                       │
                       │ (1)
                       │
                       │ (N)
                  WatchlistItem ──────── (N) Stock (stocks 앱)
```

### 인덱스 전략

1. **사용자별 조회**:
   - `Watchlist`: `user` 외래키 자동 인덱스

2. **Watchlist 내 종목 조회**:
   - `WatchlistItem`: `watchlist` 외래키 자동 인덱스
   - 복합 unique 제약: `(watchlist, stock)` - 중복 추가 방지

3. **종목별 관심 추가 여부 확인**:
   - `WatchlistItem`: `stock` 외래키 자동 인덱스

---

## 개발 예정 기능

### Portfolio (포트폴리오 실제 보유)

**Portfolio**
```python
class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    initial_cash = models.DecimalField(max_digits=15, decimal_places=2)
    current_cash = models.DecimalField(max_digits=15, decimal_places=2)
    total_value = models.DecimalField(max_digits=15, decimal_places=2)
    total_return = models.DecimalField(max_digits=8, decimal_places=2)  # %
    created_at = models.DateTimeField(auto_now_add=True)
```

**Position (보유 포지션)**
```python
class Position(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    stock = models.ForeignKey('stocks.Stock', on_delete=models.CASCADE)
    quantity = models.IntegerField()  # 보유 수량
    avg_price = models.DecimalField(max_digits=12, decimal_places=2)  # 평균 단가
    current_price = models.DecimalField(max_digits=12, decimal_places=2)  # 현재가
    market_value = models.DecimalField(max_digits=15, decimal_places=2)  # 평가액
    profit_loss = models.DecimalField(max_digits=15, decimal_places=2)  # 손익
    profit_loss_pct = models.DecimalField(max_digits=8, decimal_places=2)  # 수익률 %
    updated_at = models.DateTimeField(auto_now=True)
```

**Transaction (거래 내역)**
```python
class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
    ]

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    stock = models.ForeignKey('stocks.Stock', on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=4, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    notes = models.TextField(blank=True)
    executed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
```

자세한 내용은 추후 업데이트됩니다.
