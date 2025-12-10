"""
지표-섹터 관계 모델

거시경제 지표가 각 섹터에 미치는 영향을 정의
Neo4j 없이 Django 모델로 그래프 관계 구현
"""
from django.db import models


class SectorIndicatorRelation(models.Model):
    """
    섹터-지표 간 영향 관계

    예: 금리 상승 → 기술 섹터 (부정적), 금융 섹터 (긍정적)
    """

    class ImpactDirection(models.TextChoices):
        POSITIVE = 'positive', 'Positive'
        NEGATIVE = 'negative', 'Negative'
        NEUTRAL = 'neutral', 'Neutral'
        MIXED = 'mixed', 'Mixed'

    class ImpactStrength(models.TextChoices):
        HIGH = 'high', 'High'
        MEDIUM = 'medium', 'Medium'
        LOW = 'low', 'Low'

    # 관계 정의
    indicator = models.ForeignKey(
        'EconomicIndicator',
        on_delete=models.CASCADE,
        related_name='sector_impacts'
    )

    # 섹터 (S&P 500 GICS 섹터 기준)
    sector_code = models.CharField(
        max_length=50,
        help_text='섹터 코드 (technology, financials, healthcare 등)'
    )
    sector_name = models.CharField(max_length=100, help_text='섹터 이름')
    sector_name_ko = models.CharField(max_length=100, blank=True, help_text='한국어 섹터 이름')

    # 영향 정의
    impact_direction = models.CharField(
        max_length=20,
        choices=ImpactDirection.choices,
        default=ImpactDirection.NEUTRAL
    )
    impact_strength = models.CharField(
        max_length=20,
        choices=ImpactStrength.choices,
        default=ImpactStrength.MEDIUM
    )

    # 조건부 영향 (예: 금리가 X% 이상 오를 때만)
    condition_type = models.CharField(
        max_length=20,
        choices=[
            ('rising', 'Rising'),
            ('falling', 'Falling'),
            ('high', 'High Level'),
            ('low', 'Low Level'),
            ('any', 'Any Change'),
        ],
        default='any'
    )
    condition_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='조건 임계값 (예: 금리 +0.5%p)'
    )

    # 설명
    rationale = models.TextField(
        blank=True,
        help_text='영향 관계의 근거 설명'
    )
    rationale_ko = models.TextField(
        blank=True,
        help_text='한국어 설명'
    )

    # 메타
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'macro_sector_indicator_relation'
        verbose_name = 'Sector-Indicator Relation'
        verbose_name_plural = 'Sector-Indicator Relations'
        unique_together = ['indicator', 'sector_code', 'condition_type']
        indexes = [
            models.Index(fields=['indicator', 'impact_direction']),
            models.Index(fields=['sector_code']),
        ]

    def __str__(self):
        return f"{self.indicator.code} → {self.sector_name} ({self.impact_direction})"


class IndicatorCorrelation(models.Model):
    """
    지표 간 상관관계

    예: VIX ↔ S&P 500 (역상관), 금리 ↔ 달러 (순상관)
    """

    class CorrelationType(models.TextChoices):
        POSITIVE = 'positive', 'Positive Correlation'
        NEGATIVE = 'negative', 'Negative Correlation'
        LEADING = 'leading', 'Leading Indicator'
        LAGGING = 'lagging', 'Lagging Indicator'

    indicator_a = models.ForeignKey(
        'EconomicIndicator',
        on_delete=models.CASCADE,
        related_name='correlations_as_a'
    )
    indicator_b = models.ForeignKey(
        'EconomicIndicator',
        on_delete=models.CASCADE,
        related_name='correlations_as_b'
    )

    correlation_type = models.CharField(
        max_length=20,
        choices=CorrelationType.choices
    )

    # 상관계수 (-1 ~ +1)
    correlation_coefficient = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='최근 상관계수 (-1 ~ +1)'
    )

    # 리드/래그 관계 (일 단위)
    lead_lag_days = models.IntegerField(
        default=0,
        help_text='A가 B를 선행하는 일수 (음수면 후행)'
    )

    # 설명
    description = models.TextField(blank=True)
    description_ko = models.TextField(blank=True)

    # 계산 정보
    calculation_period_days = models.IntegerField(
        default=252,
        help_text='상관계수 계산 기간 (거래일)'
    )
    last_calculated = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'macro_indicator_correlation'
        verbose_name = 'Indicator Correlation'
        verbose_name_plural = 'Indicator Correlations'
        unique_together = ['indicator_a', 'indicator_b']

    def __str__(self):
        return f"{self.indicator_a.code} ↔ {self.indicator_b.code} ({self.correlation_type})"


# ============================================================================
# 초기 데이터 시드 함수
# ============================================================================

def seed_sector_relations():
    """
    금리-섹터 관계 초기 데이터
    """
    from .indicators import EconomicIndicator

    SECTOR_DATA = [
        # 금리 상승 시
        {
            'indicator_code': 'FEDFUNDS',
            'condition_type': 'rising',
            'relations': [
                ('technology', '기술', 'negative', 'high',
                 '할인율 상승으로 성장주 밸류에이션 하락'),
                ('financials', '금융', 'positive', 'high',
                 '예대마진 확대로 은행 수익성 개선'),
                ('real_estate', '부동산', 'negative', 'high',
                 '차입 비용 증가, 자산가치 하락 압력'),
                ('utilities', '유틸리티', 'negative', 'medium',
                 '고배당주 매력 감소, 채권 대비 열위'),
                ('healthcare', '헬스케어', 'neutral', 'low',
                 '방어적 섹터, 금리 영향 제한적'),
                ('consumer_staples', '필수소비재', 'neutral', 'low',
                 '비탄력적 수요, 금리 영향 제한적'),
                ('consumer_discretionary', '임의소비재', 'negative', 'medium',
                 '가처분소득 감소, 소비 위축 가능'),
                ('industrials', '산업재', 'mixed', 'medium',
                 '경기 민감, 금리보다 경기 사이클에 연동'),
                ('energy', '에너지', 'neutral', 'low',
                 '유가와 지정학에 더 민감'),
                ('materials', '소재', 'negative', 'medium',
                 '달러 강세 동반 시 원자재 가격 하락'),
                ('communications', '통신서비스', 'negative', 'medium',
                 '성장주 비중 높음, 금리 상승에 부정적'),
            ]
        },
        # VIX 상승 시
        {
            'indicator_code': 'VIXCLS',
            'condition_type': 'rising',
            'relations': [
                ('technology', '기술', 'negative', 'high',
                 '고베타 섹터, 시장 변동성에 민감'),
                ('financials', '금융', 'negative', 'high',
                 '신용 리스크 증가 우려'),
                ('utilities', '유틸리티', 'positive', 'medium',
                 '방어적 섹터로 자금 유입'),
                ('healthcare', '헬스케어', 'positive', 'medium',
                 '방어적 특성, 안전자산 선호 수혜'),
                ('consumer_staples', '필수소비재', 'positive', 'medium',
                 '필수재 수요 안정, 방어적 섹터'),
            ]
        }
    ]

    for data in SECTOR_DATA:
        try:
            indicator = EconomicIndicator.objects.get(code=data['indicator_code'])
        except EconomicIndicator.DoesNotExist:
            continue

        for rel in data['relations']:
            SectorIndicatorRelation.objects.update_or_create(
                indicator=indicator,
                sector_code=rel[0],
                condition_type=data['condition_type'],
                defaults={
                    'sector_name': rel[0].replace('_', ' ').title(),
                    'sector_name_ko': rel[1],
                    'impact_direction': rel[2],
                    'impact_strength': rel[3],
                    'rationale_ko': rel[4],
                }
            )
