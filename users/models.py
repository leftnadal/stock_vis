from django.db import models
from django.contrib.auth.models import AbstractUser
from stocks.models import Stock
from django.core.validators import MinValueValidator
from decimal import Decimal

# Create your models here.

class User(AbstractUser):
    """
    커스텀 유저 모델
    user_name, nick_name, favorite_stock 포함하고 있음.
    """

    user_name= models.CharField(max_length=20, default="", blank=True, null=True,)
    nick_name= models.CharField(max_length=20, default="", blank=True, null=True,)
    favorite_stock=models.ManyToManyField(Stock, max_length=100, default="", blank=True,)

    def __str__(self):
        return self.username


class Portfolio(models.Model):
    """
    사용자의 포트폴리오 - 보유 주식 정보
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portfolios')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, to_field='symbol')

    # 보유 정보
    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))],
        help_text="보유 수량"
    )
    average_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="평균 매수가"
    )

    # 목표 가격 설정
    target_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="목표 매도가"
    )
    stop_loss_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="손절가 (하한가)"
    )

    # 메모
    notes = models.TextField(blank=True, null=True, help_text="투자 메모")

    # 타임스탬프
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users_portfolio'
        unique_together = ('user', 'stock')
        indexes = [
            models.Index(fields=['user', 'stock']),
            models.Index(fields=['user', '-updated_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.stock.symbol}: {self.quantity} shares"

    @property
    def total_value(self):
        """현재 총 가치"""
        return float(self.quantity) * float(self.stock.real_time_price)

    @property
    def total_cost(self):
        """총 매수 금액"""
        return float(self.quantity) * float(self.average_price)

    @property
    def profit_loss(self):
        """손익 금액"""
        return self.total_value - self.total_cost

    @property
    def profit_loss_percentage(self):
        """손익률 (%)"""
        if self.total_cost > 0:
            return ((self.total_value - self.total_cost) / self.total_cost) * 100
        return 0

    @property
    def is_profitable(self):
        """수익 여부"""
        return self.profit_loss >= 0

    @property
    def previous_close(self):
        """전날 종가"""
        return float(self.stock.previous_close) if self.stock.previous_close else 0

    @property
    def target_achievement_rate(self):
        """목표가 달성률 (%)"""
        if self.target_price and self.average_price:
            current_price = float(self.stock.real_time_price)
            avg_price = float(self.average_price)
            target = float(self.target_price)

            # 목표 수익률 대비 현재 달성률
            target_gain = target - avg_price
            current_gain = current_price - avg_price

            if target_gain > 0:
                return (current_gain / target_gain) * 100
        return 0

    @property
    def distance_from_target(self):
        """목표가까지의 거리 (%)"""
        if self.target_price:
            current_price = float(self.stock.real_time_price)
            target = float(self.target_price)
            return ((target - current_price) / current_price) * 100
        return None

    @property
    def distance_from_stop_loss(self):
        """손절가까지의 거리 (%)"""
        if self.stop_loss_price:
            current_price = float(self.stock.real_time_price)
            stop_loss = float(self.stop_loss_price)
            return ((current_price - stop_loss) / current_price) * 100
        return None

    @property
    def portfolio_weight(self):
        """포트폴리오 내 비중 (%)"""
        # 이는 view나 serializer에서 전체 포트폴리오 가치와 비교하여 계산
        return 0  # 기본값, 실제로는 context에서 계산

    @property
    def daily_change(self):
        """일일 변동금액"""
        if self.stock.change:
            return float(self.stock.change) * float(self.quantity)
        return 0

    @property
    def daily_change_percentage(self):
        """일일 변동률 (%)"""
        if self.stock.change_percent:
            return self.stock.change_percent
        return "0%"
