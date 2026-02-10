# Stock-Vis AI Analysis System v1.0 - Phase 1

## 기반 시스템 구축 (Foundation)

**Phase**: 1 of 3   
**목표**: 동작하는 기본 분석 시스템 완성  
**선행 조건**: 없음 (첫 번째 Phase)

---

## 📋 목차

1. [Phase 1 개요](#1-phase-1-개요)
2. [Week 1: Django 모델 및 API](#2-week-1-django-모델-및-api)
3. [Week 2: Neo4j 연결 및 기본 그래프](#3-week-2-neo4j-연결-및-기본-그래프)
4. [Week 3: LLM 서비스 및 SSE](#4-week-3-llm-서비스-및-sse)
5. [Week 4: 통합 및 테스트](#5-week-4-통합-및-테스트)
6. [Phase 1 완료 기준 (DoD)](#6-phase-1-완료-기준)

---

## 1. Phase 1 개요

### 1.1 목표

Phase 1에서는 AI 분석 시스템의 **기본 골격**을 구축합니다:

- DataBasket에 종목/뉴스/재무 데이터 담기
- Neo4j와 기본 연결 및 관계 데이터 조회
- LLM을 통한 분석 생성 (단일 프롬프트)
- SSE 스트리밍 응답
- 기본적인 Redis 캐싱

### 1.2 Phase 1 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    Phase 1 아키텍처 (기본)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  사용자 → DataBasket API → 분석 요청                            │
│                              │                                   │
│                              ▼                                   │
│                    ┌─────────────────┐                          │
│                    │ ContextFormatter │                          │
│                    │ (날짜 기반)      │                          │
│                    └────────┬────────┘                          │
│                              │                                   │
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│        ┌─────────┐    ┌─────────┐    ┌─────────┐               │
│        │PostgreSQL│    │  Neo4j  │    │  Redis  │               │
│        │(바구니) │    │(관계)   │    │(캐시)   │               │
│        └─────────┘    └─────────┘    └─────────┘               │
│                              │                                   │
│                              ▼                                   │
│                    ┌─────────────────┐                          │
│                    │   LLM Service   │                          │
│                    │  (Claude Sonnet)│                          │
│                    └────────┬────────┘                          │
│                              │                                   │
│                              ▼                                   │
│                    ┌─────────────────┐                          │
│                    │  SSE Streaming  │                          │
│                    └─────────────────┘                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 주요 컴포넌트

| 컴포넌트 | 역할 | 파일 위치 |
|----------|------|-----------|
| DataBasket Model | 분석 대상 데이터 저장 | `rag_analysis/models.py` |
| BasketItem Model | 바구니 아이템 (종목, 뉴스, 재무) | `rag_analysis/models.py` |
| AnalysisSession Model | 분석 세션 관리 | `rag_analysis/models.py` |
| DateAwareContextFormatter | 날짜 기반 컨텍스트 포맷터 | `rag_analysis/services/context.py` |
| Neo4jServiceLite | Neo4j 기본 연결 | `rag_analysis/services/neo4j_service.py` |
| LLMServiceLite | Claude API 호출 | `rag_analysis/services/llm_service.py` |
| AnalysisPipelineLite | 분석 파이프라인 오케스트레이션 | `rag_analysis/services/pipeline.py` |

---

## 2. Week 1: Django 모델 및 API

### 2.1 앱 생성

```bash
cd /path/to/stock-vis/backend
python manage.py startapp rag_analysis
```

### 2.2 모델 정의

```python
# rag_analysis/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class DataBasket(models.Model):
    """사용자의 분석 데이터 바구니"""
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='baskets'
    )
    name = models.CharField(max_length=100, default='My Basket')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # 바구니 아이템 개수 제한
    MAX_ITEMS = 15
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.user.username}'s {self.name}"
    
    def can_add_item(self) -> bool:
        """아이템 추가 가능 여부"""
        return self.items.count() < self.MAX_ITEMS
    
    @property
    def items_count(self) -> int:
        return self.items.count()


class BasketItem(models.Model):
    """바구니에 담긴 개별 아이템"""
    
    class ItemType(models.TextChoices):
        STOCK = 'stock', '종목'
        NEWS = 'news', '뉴스'
        FINANCIAL = 'financial', '재무제표'
        MACRO = 'macro', '거시경제'
    
    basket = models.ForeignKey(
        DataBasket,
        on_delete=models.CASCADE,
        related_name='items'
    )
    item_type = models.CharField(
        max_length=20,
        choices=ItemType.choices
    )
    
    # 참조 ID (종목코드, 뉴스ID 등)
    reference_id = models.CharField(max_length=100)
    
    # 표시용 메타데이터
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True)
    
    # 데이터 스냅샷 (JSON)
    # 담을 당시의 데이터를 저장 (날짜 기준 명시를 위해)
    data_snapshot = models.JSONField(default=dict)
    snapshot_date = models.DateField(auto_now_add=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        # 같은 바구니에 같은 아이템 중복 방지
        unique_together = ['basket', 'item_type', 'reference_id']
    
    def __str__(self):
        return f"{self.get_item_type_display()}: {self.title}"
    
    def clean(self):
        """바구니 아이템 개수 제한 검증"""
        if self.basket_id and not self.pk:  # 새 아이템인 경우
            if not self.basket.can_add_item():
                raise ValidationError(
                    f'바구니에는 최대 {DataBasket.MAX_ITEMS}개의 '
                    f'아이템만 담을 수 있습니다.'
                )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class AnalysisSession(models.Model):
    """분석 세션 (대화 컨텍스트 유지)"""
    
    class Status(models.TextChoices):
        ACTIVE = 'active', '활성'
        COMPLETED = 'completed', '완료'
        ERROR = 'error', '오류'
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='analysis_sessions'
    )
    basket = models.ForeignKey(
        DataBasket,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sessions'
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    
    # 세션 메타데이터
    title = models.CharField(max_length=200, blank=True)
    
    # 탐험 경로 기록
    exploration_path = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Session {self.id} - {self.user.username}"
    
    def add_exploration(self, entity_type: str, entity_id: str, reason: str):
        """탐험 경로 추가"""
        self.exploration_path.append({
            'type': entity_type,
            'id': entity_id,
            'reason': reason,
            'timestamp': timezone.now().isoformat()
        })
        self.save(update_fields=['exploration_path', 'updated_at'])


class AnalysisMessage(models.Model):
    """분석 세션 내 메시지"""
    
    class Role(models.TextChoices):
        USER = 'user', '사용자'
        ASSISTANT = 'assistant', '어시스턴트'
        SYSTEM = 'system', '시스템'
    
    session = models.ForeignKey(
        AnalysisSession,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices
    )
    content = models.TextField()
    
    # LLM 제안 (JSON)
    suggestions = models.JSONField(default=list)
    
    # 토큰 사용량 추적
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.get_role_display()}: {self.content[:50]}..."
```

### 2.3 Serializers

```python
# rag_analysis/serializers.py

from rest_framework import serializers
from .models import DataBasket, BasketItem, AnalysisSession, AnalysisMessage


class BasketItemSerializer(serializers.ModelSerializer):
    """바구니 아이템 시리얼라이저"""
    
    item_type_display = serializers.CharField(
        source='get_item_type_display', 
        read_only=True
    )
    
    class Meta:
        model = BasketItem
        fields = [
            'id', 'item_type', 'item_type_display',
            'reference_id', 'title', 'subtitle',
            'data_snapshot', 'snapshot_date', 'created_at'
        ]
        read_only_fields = ['snapshot_date', 'created_at']


class DataBasketSerializer(serializers.ModelSerializer):
    """데이터 바구니 시리얼라이저"""
    
    items = BasketItemSerializer(many=True, read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    can_add_item = serializers.SerializerMethodField()
    
    class Meta:
        model = DataBasket
        fields = [
            'id', 'name', 'description', 
            'items', 'items_count', 'can_add_item',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_can_add_item(self, obj) -> bool:
        return obj.can_add_item()


class AnalysisMessageSerializer(serializers.ModelSerializer):
    """분석 메시지 시리얼라이저"""
    
    class Meta:
        model = AnalysisMessage
        fields = [
            'id', 'role', 'content', 'suggestions',
            'input_tokens', 'output_tokens', 'created_at'
        ]
        read_only_fields = ['created_at']


class AnalysisSessionSerializer(serializers.ModelSerializer):
    """분석 세션 시리얼라이저"""
    
    messages = AnalysisMessageSerializer(many=True, read_only=True)
    basket = DataBasketSerializer(read_only=True)
    basket_id = serializers.PrimaryKeyRelatedField(
        queryset=DataBasket.objects.all(),
        source='basket',
        write_only=True
    )
    
    class Meta:
        model = AnalysisSession
        fields = [
            'id', 'basket', 'basket_id', 'status', 'title',
            'exploration_path', 'messages',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['status', 'exploration_path', 'created_at', 'updated_at']
```

### 2.4 ViewSets

```python
# rag_analysis/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import DataBasket, BasketItem, AnalysisSession
from .serializers import (
    DataBasketSerializer, 
    BasketItemSerializer,
    AnalysisSessionSerializer
)


class DataBasketViewSet(viewsets.ModelViewSet):
    """데이터 바구니 ViewSet"""
    
    serializer_class = DataBasketSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return DataBasket.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        """바구니에 아이템 추가"""
        basket = self.get_object()
        
        if not basket.can_add_item():
            return Response(
                {'error': f'바구니에는 최대 {DataBasket.MAX_ITEMS}개의 아이템만 담을 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = BasketItemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(basket=basket)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'], url_path='items/(?P<item_id>[^/.]+)')
    def remove_item(self, request, pk=None, item_id=None):
        """바구니에서 아이템 제거"""
        basket = self.get_object()
        item = get_object_or_404(BasketItem, basket=basket, pk=item_id)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['delete'])
    def clear(self, request, pk=None):
        """바구니 비우기"""
        basket = self.get_object()
        basket.items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AnalysisSessionViewSet(viewsets.ModelViewSet):
    """분석 세션 ViewSet"""
    
    serializer_class = AnalysisSessionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return AnalysisSession.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
```

### 2.5 URL 설정

```python
# rag_analysis/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DataBasketViewSet, AnalysisSessionViewSet

router = DefaultRouter()
router.register(r'baskets', DataBasketViewSet, basename='basket')
router.register(r'sessions', AnalysisSessionViewSet, basename='session')

urlpatterns = [
    path('', include(router.urls)),
]

# config/urls.py에 추가
# path('api/v1/rag/', include('rag_analysis.urls')),
```

### 2.6 Week 1 완료 기준

- [ ] `rag_analysis` 앱 생성
- [ ] 4개 모델 마이그레이션 완료 (`DataBasket`, `BasketItem`, `AnalysisSession`, `AnalysisMessage`)
- [ ] BasketItem 15개 제한 동작 확인
- [ ] CRUD API 테스트 통과
- [ ] Admin 페이지 등록

---

## 3. Week 2: Neo4j 연결 및 기본 그래프

### 3.1 Neo4j 드라이버 설정

```python
# rag_analysis/services/neo4j_driver.py

from neo4j import AsyncGraphDatabase
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# 싱글톤 드라이버 인스턴스
_driver = None


def get_neo4j_driver():
    """Neo4j 드라이버 싱글톤"""
    global _driver
    
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            max_connection_pool_size=50,
        )
        logger.info("Neo4j driver initialized")
    
    return _driver


async def close_neo4j_driver():
    """드라이버 종료 (앱 종료 시)"""
    global _driver
    if _driver:
        await _driver.close()
        _driver = None
        logger.info("Neo4j driver closed")
```

### 3.2 Neo4j Service

```python
# rag_analysis/services/neo4j_service.py

from typing import Optional
import asyncio
import logging
from .neo4j_driver import get_neo4j_driver

logger = logging.getLogger(__name__)


class Neo4jServiceLite:
    """Neo4j 기본 서비스 (Phase 1)"""
    
    # 쿼리 타임아웃 (ms)
    QUERY_TIMEOUT = 2000
    
    def __init__(self):
        self.driver = get_neo4j_driver()
    
    async def get_stock_relationships(
        self, 
        symbol: str,
        max_depth: int = 1
    ) -> dict:
        """종목의 관계 정보 조회"""
        
        try:
            async with asyncio.timeout(self.QUERY_TIMEOUT / 1000):
                async with self.driver.session() as session:
                    # 공급망 관계
                    supply_chain = await self._get_supply_chain(session, symbol)
                    
                    # 경쟁사 관계
                    competitors = await self._get_competitors(session, symbol)
                    
                    # 섹터 동료
                    sector_peers = await self._get_sector_peers(session, symbol)
                    
                    return {
                        'symbol': symbol,
                        'supply_chain': supply_chain,
                        'competitors': competitors,
                        'sector_peers': sector_peers,
                        '_meta': {
                            'depth': max_depth,
                            'source': 'neo4j'
                        }
                    }
                    
        except asyncio.TimeoutError:
            logger.warning(f"Neo4j query timeout for {symbol}")
            return self._empty_relationships(symbol, 'timeout')
        except Exception as e:
            logger.error(f"Neo4j error for {symbol}: {e}")
            return self._empty_relationships(symbol, str(e))
    
    async def _get_supply_chain(self, session, symbol: str) -> list:
        """공급망 관계 조회"""
        result = await session.run("""
            MATCH (s:Stock {symbol: $symbol})-[r:SUPPLIES|SUPPLIED_BY]-(related:Stock)
            RETURN related.symbol as symbol, 
                   related.name as name,
                   type(r) as relationship,
                   r.strength as strength
            ORDER BY r.strength DESC
            LIMIT 5
        """, symbol=symbol)
        
        return [dict(record) async for record in result]
    
    async def _get_competitors(self, session, symbol: str) -> list:
        """경쟁사 조회"""
        result = await session.run("""
            MATCH (s:Stock {symbol: $symbol})-[r:COMPETES_WITH]-(related:Stock)
            RETURN related.symbol as symbol,
                   related.name as name,
                   r.overlap_score as overlap
            ORDER BY r.overlap_score DESC
            LIMIT 5
        """, symbol=symbol)
        
        return [dict(record) async for record in result]
    
    async def _get_sector_peers(self, session, symbol: str) -> list:
        """동일 섹터 종목 조회"""
        result = await session.run("""
            MATCH (s:Stock {symbol: $symbol})-[:BELONGS_TO]->(sector:Sector)
                  <-[:BELONGS_TO]-(peer:Stock)
            WHERE peer.symbol <> $symbol
            RETURN peer.symbol as symbol,
                   peer.name as name,
                   sector.name as sector
            ORDER BY peer.market_cap DESC
            LIMIT 5
        """, symbol=symbol)
        
        return [dict(record) async for record in result]
    
    def _empty_relationships(self, symbol: str, error: str) -> dict:
        """빈 관계 반환 (Graceful Degradation)"""
        return {
            'symbol': symbol,
            'supply_chain': [],
            'competitors': [],
            'sector_peers': [],
            '_meta': {
                'source': 'fallback',
                '_error': error
            }
        }
    
    async def health_check(self) -> bool:
        """Neo4j 연결 상태 확인"""
        try:
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 as n")
                record = await result.single()
                return record['n'] == 1
        except Exception:
            return False
```

### 3.3 Neo4j Seeding Command

```python
# rag_analysis/management/commands/seed_neo4j_graph.py

from django.core.management.base import BaseCommand
from stocks.models import Stock
from neo4j import GraphDatabase
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Seed Neo4j graph with stock relationships'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding'
        )
    
    def handle(self, *args, **options):
        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        
        with driver.session() as session:
            if options['clear']:
                self.stdout.write('Clearing existing data...')
                session.run("MATCH (n) DETACH DELETE n")
            
            # 인덱스 생성
            self._create_indexes(session)
            
            # 종목 노드 생성
            self._seed_stocks(session)
            
            # 섹터 노드 및 관계 생성
            self._seed_sectors(session)
            
            # 관계 생성 (예시 데이터)
            self._seed_relationships(session)
        
        driver.close()
        self.stdout.write(self.style.SUCCESS('Neo4j seeding completed!'))
    
    def _create_indexes(self, session):
        """인덱스 생성"""
        indexes = [
            "CREATE INDEX stock_symbol IF NOT EXISTS FOR (s:Stock) ON (s.symbol)",
            "CREATE INDEX sector_name IF NOT EXISTS FOR (s:Sector) ON (s.name)",
            "CREATE INDEX news_id IF NOT EXISTS FOR (n:News) ON (n.id)",
        ]
        for idx in indexes:
            session.run(idx)
        self.stdout.write('Indexes created')
    
    def _seed_stocks(self, session):
        """종목 노드 생성"""
        stocks = Stock.objects.all()[:500]  # 상위 500개
        
        for stock in stocks:
            session.run("""
                MERGE (s:Stock {symbol: $symbol})
                SET s.name = $name,
                    s.sector = $sector,
                    s.industry = $industry
            """, 
                symbol=stock.symbol,
                name=stock.name,
                sector=stock.sector,
                industry=stock.industry
            )
        
        self.stdout.write(f'{stocks.count()} stocks seeded')
    
    def _seed_sectors(self, session):
        """섹터 노드 및 관계 생성"""
        sectors = Stock.objects.values_list('sector', flat=True).distinct()
        
        for sector in sectors:
            if sector:
                # 섹터 노드 생성
                session.run("""
                    MERGE (sec:Sector {name: $name})
                """, name=sector)
                
                # 종목-섹터 관계 생성
                session.run("""
                    MATCH (s:Stock {sector: $sector})
                    MATCH (sec:Sector {name: $sector})
                    MERGE (s)-[:BELONGS_TO]->(sec)
                """, sector=sector)
        
        self.stdout.write(f'{len(list(sectors))} sectors seeded')
    
    def _seed_relationships(self, session):
        """관계 생성 (예시)"""
        # 실제로는 외부 데이터나 분석 결과로 관계를 생성
        # 여기서는 예시로 일부 관계만 생성
        
        relationships = [
            # 공급망 예시
            ('AAPL', 'TSM', 'SUPPLIED_BY', 0.9),
            ('AAPL', 'QCOM', 'SUPPLIED_BY', 0.7),
            ('NVDA', 'TSM', 'SUPPLIED_BY', 0.95),
            
            # 경쟁 관계 예시
            ('AAPL', 'MSFT', 'COMPETES_WITH', 0.6),
            ('GOOGL', 'MSFT', 'COMPETES_WITH', 0.8),
            ('AMD', 'NVDA', 'COMPETES_WITH', 0.9),
        ]
        
        for source, target, rel_type, strength in relationships:
            if rel_type == 'SUPPLIED_BY':
                session.run("""
                    MATCH (s:Stock {symbol: $source})
                    MATCH (t:Stock {symbol: $target})
                    MERGE (s)-[r:SUPPLIED_BY]->(t)
                    SET r.strength = $strength
                """, source=source, target=target, strength=strength)
            elif rel_type == 'COMPETES_WITH':
                session.run("""
                    MATCH (s:Stock {symbol: $source})
                    MATCH (t:Stock {symbol: $target})
                    MERGE (s)-[r:COMPETES_WITH]-(t)
                    SET r.overlap_score = $strength
                """, source=source, target=target, strength=strength)
        
        self.stdout.write(f'{len(relationships)} relationships seeded')
```

### 3.4 Week 2 완료 기준

- [ ] Neo4j Aura 연결 설정
- [ ] 싱글톤 드라이버 구현
- [ ] `seed_neo4j_graph` 명령어 동작
- [ ] 종목 관계 조회 API 동작
- [ ] Graceful Degradation 테스트 (Neo4j 다운 시)

---

## 4. Week 3: LLM 서비스 및 SSE

### 4.1 Context Formatter

```python
# rag_analysis/services/context.py

from datetime import date
from typing import List
from ..models import DataBasket, BasketItem


class DateAwareContextFormatter:
    """날짜 기반 컨텍스트 포맷터 (Phase 1)"""
    
    def __init__(self, basket: DataBasket):
        self.basket = basket
        self.today = date.today()
    
    def format(self) -> str:
        """바구니 컨텍스트 포맷팅"""
        sections = []
        
        # 헤더
        sections.append(self._format_header())
        
        # 아이템별 포맷팅
        for item in self.basket.items.all():
            sections.append(self._format_item(item))
        
        return "\n\n".join(sections)
    
    def _format_header(self) -> str:
        """헤더 섹션"""
        return f"""## 분석 컨텍스트
분석 기준일: {self.today.isoformat()}
바구니: {self.basket.name}
아이템 수: {self.basket.items_count}개"""
    
    def _format_item(self, item: BasketItem) -> str:
        """아이템 포맷팅"""
        if item.item_type == BasketItem.ItemType.STOCK:
            return self._format_stock(item)
        elif item.item_type == BasketItem.ItemType.NEWS:
            return self._format_news(item)
        elif item.item_type == BasketItem.ItemType.FINANCIAL:
            return self._format_financial(item)
        elif item.item_type == BasketItem.ItemType.MACRO:
            return self._format_macro(item)
        return ""
    
    def _format_stock(self, item: BasketItem) -> str:
        """종목 포맷팅"""
        data = item.data_snapshot
        return f"""### 종목: {item.title} ({item.reference_id})
- 섹터: {data.get('sector', 'N/A')}
- 시가총액: ${data.get('market_cap', 0):,.0f} ({item.snapshot_date} 기준)
- PER: {data.get('pe_ratio', 'N/A')}
- 52주 최고/최저: ${data.get('high_52w', 0):.2f} / ${data.get('low_52w', 0):.2f}"""
    
    def _format_news(self, item: BasketItem) -> str:
        """뉴스 포맷팅"""
        data = item.data_snapshot
        return f"""### 뉴스: {item.title}
- 발행일: {data.get('published_date', 'N/A')}
- 출처: {data.get('source', 'N/A')}
- 감성: {data.get('sentiment', 'N/A')}
- 요약: {data.get('summary', item.subtitle)[:200]}..."""
    
    def _format_financial(self, item: BasketItem) -> str:
        """재무제표 포맷팅"""
        data = item.data_snapshot
        period = data.get('period', 'N/A')
        return f"""### 재무제표: {item.title} ({period} 기준)
- 매출: ${data.get('revenue', 0):,.0f}
- 영업이익: ${data.get('operating_income', 0):,.0f}
- 순이익: ${data.get('net_income', 0):,.0f}
- EPS: ${data.get('eps', 0):.2f}"""
    
    def _format_macro(self, item: BasketItem) -> str:
        """거시경제 지표 포맷팅"""
        data = item.data_snapshot
        return f"""### 거시지표: {item.title}
- 값: {data.get('value', 'N/A')}
- 기준일: {data.get('date', item.snapshot_date)}
- 변화: {data.get('change', 'N/A')}"""
```

### 4.2 LLM Service

```python
# rag_analysis/services/llm_service.py

from anthropic import AsyncAnthropic
from django.conf import settings
from typing import AsyncGenerator
import logging

logger = logging.getLogger(__name__)


class LLMServiceLite:
    """LLM 서비스 (Phase 1)"""
    
    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 2000
    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 2, 4]  # 지수 백오프
    
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    def get_system_prompt(self) -> str:
        """시스템 프롬프트"""
        return """당신은 Stock-Vis의 투자 분석 AI 어시스턴트입니다.

## 역할
사용자가 제공한 종목, 뉴스, 재무 데이터를 분석하여 투자 인사이트를 제공합니다.

## 규칙
1. **날짜 명시**: 모든 수치와 데이터에는 반드시 기준 날짜를 명시하세요.
   - 가격: "2024-12-13 기준 $150.25"
   - 재무: "2024 Q3 기준 매출 $100B"
   
2. **면책조항**: 응답 마지막에 다음 문구를 포함하세요:
   "※ 본 분석은 정보 제공 목적이며, 투자 권유가 아닙니다."

3. **탐험 제안**: 분석 후 관련 종목이나 주제를 1-2개 제안하세요.
   <suggestions> 태그로 감싸서 제공:
   <suggestions>
   - TSM: AAPL의 주요 반도체 공급사로, 파운드리 시장 동향 파악에 유용
   - QCOM: 모바일 칩셋 경쟁 구도 분석 시 참고
   </suggestions>

## 출력 형식
1. 핵심 분석 (2-3 문단)
2. 주요 지표 해석
3. 리스크 요인
4. 탐험 제안 (<suggestions> 태그)
5. 면책조항"""
    
    async def generate_stream(
        self, 
        context: str, 
        question: str
    ) -> AsyncGenerator[dict, None]:
        """스트리밍 응답 생성"""
        
        messages = [
            {"role": "user", "content": f"{context}\n\n질문: {question}"}
        ]
        
        retry_count = 0
        while retry_count < self.MAX_RETRIES:
            try:
                async with self.client.messages.stream(
                    model=self.MODEL,
                    max_tokens=self.MAX_TOKENS,
                    system=self.get_system_prompt(),
                    messages=messages
                ) as stream:
                    async for event in stream:
                        if event.type == "content_block_delta":
                            yield {
                                'type': 'delta',
                                'content': event.delta.text
                            }
                    
                    # 최종 메시지
                    final_message = await stream.get_final_message()
                    yield {
                        'type': 'final',
                        'input_tokens': final_message.usage.input_tokens,
                        'output_tokens': final_message.usage.output_tokens
                    }
                    return
                    
            except Exception as e:
                retry_count += 1
                if retry_count >= self.MAX_RETRIES:
                    logger.error(f"LLM failed after {self.MAX_RETRIES} retries: {e}")
                    yield {
                        'type': 'error',
                        'message': '분석 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'
                    }
                    return
                
                delay = self.RETRY_DELAYS[retry_count - 1]
                logger.warning(f"LLM retry {retry_count}/{self.MAX_RETRIES} after {delay}s")
                await asyncio.sleep(delay)


class ResponseParser:
    """LLM 응답 파서"""
    
    @staticmethod
    def parse_suggestions(content: str) -> tuple[str, list]:
        """응답에서 suggestions 추출"""
        import re
        
        # <suggestions> 태그 추출
        pattern = r'<suggestions>(.*?)</suggestions>'
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            return content, []
        
        suggestions_text = match.group(1).strip()
        main_content = re.sub(pattern, '', content, flags=re.DOTALL).strip()
        
        # 제안 파싱
        suggestions = []
        for line in suggestions_text.split('\n'):
            line = line.strip()
            if line.startswith('-'):
                line = line[1:].strip()
                if ':' in line:
                    symbol, reason = line.split(':', 1)
                    suggestions.append({
                        'symbol': symbol.strip(),
                        'reason': reason.strip()
                    })
        
        return main_content, suggestions
```

### 4.3 Analysis Pipeline

```python
# rag_analysis/services/pipeline.py

from typing import AsyncGenerator
from django.utils import timezone
from asgiref.sync import sync_to_async

from ..models import AnalysisSession, AnalysisMessage
from .context import DateAwareContextFormatter
from .neo4j_service import Neo4jServiceLite
from .llm_service import LLMServiceLite, ResponseParser

import logging

logger = logging.getLogger(__name__)


class AnalysisPipelineLite:
    """분석 파이프라인 (Phase 1)"""
    
    def __init__(self, session: AnalysisSession):
        self.session = session
        self.neo4j = Neo4jServiceLite()
        self.llm = LLMServiceLite()
    
    async def analyze(self, question: str) -> AsyncGenerator[dict, None]:
        """분석 실행 (SSE 스트리밍)"""
        
        try:
            # Phase 1: 준비
            yield {'phase': 'preparing', 'message': '분석 준비 중...'}
            
            # 컨텍스트 구성
            context = await self._build_context()
            yield {'phase': 'context_ready', 'message': '컨텍스트 준비 완료'}
            
            # Phase 2: 분석
            yield {'phase': 'analyzing', 'message': '분석 중...'}
            
            # LLM 스트리밍
            full_response = ""
            async for chunk in self.llm.generate_stream(context, question):
                if chunk['type'] == 'delta':
                    full_response += chunk['content']
                    yield {
                        'phase': 'streaming',
                        'chunk': chunk['content']
                    }
                elif chunk['type'] == 'final':
                    # 응답 파싱
                    main_content, suggestions = ResponseParser.parse_suggestions(full_response)
                    
                    # 메시지 저장
                    await self._save_messages(question, main_content, suggestions, chunk)
                    
                    yield {
                        'phase': 'complete',
                        'data': {
                            'content': main_content,
                            'suggestions': suggestions,
                            'usage': {
                                'input_tokens': chunk['input_tokens'],
                                'output_tokens': chunk['output_tokens']
                            }
                        }
                    }
                elif chunk['type'] == 'error':
                    await self._update_session_status('error')
                    yield {
                        'phase': 'error',
                        'message': chunk['message']
                    }
                    
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            await self._update_session_status('error')
            yield {
                'phase': 'error',
                'message': '분석 중 오류가 발생했습니다.'
            }
    
    async def _build_context(self) -> str:
        """컨텍스트 구성"""
        parts = []
        
        # 바구니 컨텍스트
        basket = await sync_to_async(lambda: self.session.basket)()
        if basket:
            formatter = DateAwareContextFormatter(basket)
            parts.append(await sync_to_async(formatter.format)())
        
        # 그래프 컨텍스트 (첫 번째 종목만)
        first_stock = await self._get_first_stock_symbol()
        if first_stock:
            graph_context = await self.neo4j.get_stock_relationships(first_stock)
            if graph_context.get('_meta', {}).get('source') != 'fallback':
                parts.append(self._format_graph_context(graph_context))
        
        return "\n\n---\n\n".join(parts)
    
    async def _get_first_stock_symbol(self) -> str:
        """바구니의 첫 번째 종목 심볼"""
        basket = await sync_to_async(lambda: self.session.basket)()
        if not basket:
            return None
        
        stock_item = await sync_to_async(
            lambda: basket.items.filter(item_type='stock').first()
        )()
        
        return stock_item.reference_id if stock_item else None
    
    def _format_graph_context(self, graph: dict) -> str:
        """그래프 컨텍스트 포맷팅"""
        lines = [f"### 관계 정보: {graph['symbol']}"]
        
        if graph['supply_chain']:
            suppliers = ", ".join([s['symbol'] for s in graph['supply_chain'][:3]])
            lines.append(f"- 공급망: {suppliers}")
        
        if graph['competitors']:
            competitors = ", ".join([c['symbol'] for c in graph['competitors'][:3]])
            lines.append(f"- 경쟁사: {competitors}")
        
        if graph['sector_peers']:
            peers = ", ".join([p['symbol'] for p in graph['sector_peers'][:3]])
            lines.append(f"- 섹터 동료: {peers}")
        
        return "\n".join(lines)
    
    @sync_to_async
    def _save_messages(self, question, content, suggestions, usage):
        """메시지 저장"""
        # 사용자 메시지
        AnalysisMessage.objects.create(
            session=self.session,
            role=AnalysisMessage.Role.USER,
            content=question
        )
        
        # 어시스턴트 메시지
        AnalysisMessage.objects.create(
            session=self.session,
            role=AnalysisMessage.Role.ASSISTANT,
            content=content,
            suggestions=suggestions,
            input_tokens=usage.get('input_tokens', 0),
            output_tokens=usage.get('output_tokens', 0)
        )
    
    @sync_to_async
    def _update_session_status(self, status):
        """세션 상태 업데이트"""
        self.session.status = status
        self.session.save(update_fields=['status', 'updated_at'])
```

### 4.4 SSE Streaming View

```python
# rag_analysis/views.py (추가)

from django.http import StreamingHttpResponse
from rest_framework.decorators import action
from asgiref.sync import async_to_sync
import json


class AnalysisSessionViewSet(viewsets.ModelViewSet):
    # ... 기존 코드 ...
    
    @action(detail=True, methods=['post'], url_path='chat/stream')
    def chat_stream(self, request, pk=None):
        """SSE 스트리밍 분석"""
        session = self.get_object()
        question = request.data.get('message', '')
        
        if not question:
            return Response(
                {'error': '질문을 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        def event_stream():
            from .services.pipeline import AnalysisPipelineLite
            pipeline = AnalysisPipelineLite(session)
            
            async def generate():
                async for event in pipeline.analyze(question):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            # async generator를 sync로 변환
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                gen = generate()
                while True:
                    try:
                        event = loop.run_until_complete(gen.__anext__())
                        yield event
                    except StopAsyncIteration:
                        break
            finally:
                loop.close()
        
        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
```

### 4.5 Week 3 완료 기준

- [ ] DateAwareContextFormatter 동작
- [ ] LLMServiceLite 스트리밍 동작
- [ ] SSE 엔드포인트 동작
- [ ] 응답에서 suggestions 파싱
- [ ] 메시지 저장 동작

---

## 5. Week 4: 통합 및 테스트

### 5.1 Signal 기반 동기화

```python
# rag_analysis/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from stocks.models import Stock
from .tasks import sync_stock_to_neo4j, delete_stock_from_neo4j


@receiver(post_save, sender=Stock)
def stock_saved(sender, instance, created, **kwargs):
    """Stock 저장 시 Neo4j 동기화"""
    sync_stock_to_neo4j.delay(
        symbol=instance.symbol,
        name=instance.name,
        sector=instance.sector,
        industry=instance.industry
    )


@receiver(post_delete, sender=Stock)
def stock_deleted(sender, instance, **kwargs):
    """Stock 삭제 시 Neo4j에서도 삭제"""
    delete_stock_from_neo4j.delay(symbol=instance.symbol)
```

```python
# rag_analysis/tasks.py

from celery import shared_task
from neo4j import GraphDatabase
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task
def sync_stock_to_neo4j(symbol, name, sector, industry):
    """종목 정보를 Neo4j에 동기화"""
    driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    )
    
    try:
        with driver.session() as session:
            session.run("""
                MERGE (s:Stock {symbol: $symbol})
                SET s.name = $name,
                    s.sector = $sector,
                    s.industry = $industry,
                    s.updated_at = datetime()
            """, symbol=symbol, name=name, sector=sector, industry=industry)
            
            # 섹터 관계 업데이트
            if sector:
                session.run("""
                    MERGE (sec:Sector {name: $sector})
                    WITH sec
                    MATCH (s:Stock {symbol: $symbol})
                    MERGE (s)-[:BELONGS_TO]->(sec)
                """, symbol=symbol, sector=sector)
                
        logger.info(f"Synced {symbol} to Neo4j")
    except Exception as e:
        logger.error(f"Failed to sync {symbol}: {e}")
    finally:
        driver.close()


@shared_task
def delete_stock_from_neo4j(symbol):
    """종목을 Neo4j에서 삭제"""
    driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    )
    
    try:
        with driver.session() as session:
            session.run("""
                MATCH (s:Stock {symbol: $symbol})
                DETACH DELETE s
            """, symbol=symbol)
        logger.info(f"Deleted {symbol} from Neo4j")
    except Exception as e:
        logger.error(f"Failed to delete {symbol}: {e}")
    finally:
        driver.close()
```

### 5.2 기본 Redis 캐싱

```python
# rag_analysis/services/cache.py

from django.core.cache import cache
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class BasicCacheService:
    """기본 캐시 서비스 (Phase 1)"""
    
    # TTL 설정 (초)
    TTL_GRAPH_QUERY = 3600  # 1시간
    TTL_LLM_RESPONSE = 21600  # 6시간
    
    @staticmethod
    def _make_key(prefix: str, *args) -> str:
        """캐시 키 생성"""
        data = json.dumps(args, sort_keys=True)
        hash_value = hashlib.md5(data.encode()).hexdigest()[:12]
        return f"{prefix}:{hash_value}"
    
    def get_graph_context(self, symbol: str) -> dict | None:
        """그래프 컨텍스트 캐시 조회"""
        key = self._make_key('graph', symbol)
        return cache.get(key)
    
    def set_graph_context(self, symbol: str, data: dict):
        """그래프 컨텍스트 캐시 저장"""
        key = self._make_key('graph', symbol)
        cache.set(key, data, self.TTL_GRAPH_QUERY)
        logger.debug(f"Cached graph context for {symbol}")
    
    def get_llm_response(self, question: str, entities: list) -> dict | None:
        """LLM 응답 캐시 조회"""
        key = self._make_key('llm', question, entities)
        return cache.get(key)
    
    def set_llm_response(self, question: str, entities: list, response: dict):
        """LLM 응답 캐시 저장"""
        key = self._make_key('llm', question, entities)
        cache.set(key, response, self.TTL_LLM_RESPONSE)
        logger.debug(f"Cached LLM response")
    
    def invalidate_graph(self, symbol: str):
        """그래프 캐시 무효화"""
        key = self._make_key('graph', symbol)
        cache.delete(key)
```

### 5.3 E2E 테스트

```python
# rag_analysis/tests/test_e2e.py

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from unittest.mock import patch, AsyncMock
import json

from ..models import DataBasket, BasketItem, AnalysisSession

User = get_user_model()


class AnalysisE2ETest(TestCase):
    """E2E 테스트"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    def test_basket_crud(self):
        """바구니 CRUD 테스트"""
        # Create
        response = self.client.post('/api/v1/rag/baskets/', {
            'name': 'Test Basket'
        })
        self.assertEqual(response.status_code, 201)
        basket_id = response.data['id']
        
        # Read
        response = self.client.get(f'/api/v1/rag/baskets/{basket_id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'Test Basket')
        
        # Update
        response = self.client.patch(f'/api/v1/rag/baskets/{basket_id}/', {
            'name': 'Updated Basket'
        })
        self.assertEqual(response.status_code, 200)
        
        # Delete
        response = self.client.delete(f'/api/v1/rag/baskets/{basket_id}/')
        self.assertEqual(response.status_code, 204)
    
    def test_basket_item_limit(self):
        """바구니 아이템 15개 제한 테스트"""
        basket = DataBasket.objects.create(user=self.user, name='Test')
        
        # 15개 추가 (성공)
        for i in range(15):
            response = self.client.post(
                f'/api/v1/rag/baskets/{basket.id}/add_item/',
                {
                    'item_type': 'stock',
                    'reference_id': f'TEST{i}',
                    'title': f'Test Stock {i}'
                }
            )
            self.assertEqual(response.status_code, 201)
        
        # 16번째 추가 (실패)
        response = self.client.post(
            f'/api/v1/rag/baskets/{basket.id}/add_item/',
            {
                'item_type': 'stock',
                'reference_id': 'TEST16',
                'title': 'Test Stock 16'
            }
        )
        self.assertEqual(response.status_code, 400)
    
    def test_session_create(self):
        """세션 생성 테스트"""
        basket = DataBasket.objects.create(user=self.user, name='Test')
        
        response = self.client.post('/api/v1/rag/sessions/', {
            'basket_id': basket.id,
            'title': 'Test Session'
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'active')
    
    @patch('rag_analysis.services.llm_service.LLMServiceLite.generate_stream')
    @patch('rag_analysis.services.neo4j_service.Neo4jServiceLite.get_stock_relationships')
    def test_analysis_happy_path(self, mock_neo4j, mock_llm):
        """전체 분석 흐름 테스트"""
        # Mock 설정
        mock_neo4j.return_value = {
            'symbol': 'AAPL',
            'supply_chain': [{'symbol': 'TSM', 'name': 'TSMC'}],
            'competitors': [],
            'sector_peers': [],
            '_meta': {'source': 'neo4j'}
        }
        
        async def mock_stream(*args, **kwargs):
            yield {'type': 'delta', 'content': 'Test analysis '}
            yield {'type': 'delta', 'content': '<suggestions>- TSM: supplier</suggestions>'}
            yield {'type': 'final', 'input_tokens': 100, 'output_tokens': 50}
        
        mock_llm.return_value = mock_stream()
        
        # 바구니 생성 및 아이템 추가
        basket = DataBasket.objects.create(user=self.user, name='Test')
        BasketItem.objects.create(
            basket=basket,
            item_type='stock',
            reference_id='AAPL',
            title='Apple Inc.',
            data_snapshot={'sector': 'Technology'}
        )
        
        # 세션 생성
        session = AnalysisSession.objects.create(
            user=self.user,
            basket=basket
        )
        
        # 분석 요청 (SSE)
        response = self.client.post(
            f'/api/v1/rag/sessions/{session.id}/chat/stream/',
            {'message': 'AAPL 분석해줘'}
        )
        self.assertEqual(response.status_code, 200)
    
    @patch('rag_analysis.services.neo4j_service.Neo4jServiceLite.get_stock_relationships')
    def test_neo4j_failure_graceful(self, mock_neo4j):
        """Neo4j 실패 시 분석 계속 동작 테스트"""
        mock_neo4j.return_value = {
            'symbol': 'AAPL',
            'supply_chain': [],
            'competitors': [],
            'sector_peers': [],
            '_meta': {'source': 'fallback', '_error': 'Connection failed'}
        }
        
        # 분석이 계속 진행되어야 함
        basket = DataBasket.objects.create(user=self.user, name='Test')
        session = AnalysisSession.objects.create(user=self.user, basket=basket)
        
        # Neo4j 없이도 파이프라인이 동작해야 함
        from ..services.pipeline import AnalysisPipelineLite
        pipeline = AnalysisPipelineLite(session)
        
        # context 빌드가 실패하지 않아야 함
        import asyncio
        context = asyncio.run(pipeline._build_context())
        self.assertIsNotNone(context)
```

### 5.4 Week 4 완료 기준

- [ ] Signal 기반 Neo4j 동기화 동작
- [ ] 기본 Redis 캐싱 동작
- [ ] E2E 테스트 통과
- [ ] API 문서화 (Swagger)
- [ ] 환경변수 설정 문서

---

## 6. Phase 1 완료 기준

### 6.1 기능 체크리스트

- [ ] DataBasket CRUD API
- [ ] BasketItem CRUD API (Hard Limit 15개)
- [ ] AnalysisSession 생성 API
- [ ] SSE 스트리밍 분석 API
- [ ] 단일 프롬프트 (분석 + 제안)
- [ ] 날짜 기준 명시 (모든 수치)
- [ ] 탐험 제안 파싱 및 표시

### 6.2 기술 체크리스트

- [ ] Django 모델 마이그레이션
- [ ] Neo4j Seeding Command 동작
- [ ] Neo4j 싱글톤 드라이버
- [ ] Stock Signal → Neo4j 동기화
- [ ] Graceful Degradation (Neo4j 실패 시)
- [ ] SSE 스트리밍 동작
- [ ] LLM 재시도 로직 (3회)
- [ ] 기본 Redis 캐싱

### 6.3 품질 체크리스트

- [ ] 응답에 항상 날짜 포함 검증
- [ ] 면책조항 포함 검증
- [ ] TTFT (Time To First Token) 5초 이내
- [ ] BasketItem 15개 제한 동작
- [ ] Neo4j 실패 시 분석 계속 동작
- [ ] E2E 테스트 통과

### 6.4 문서 체크리스트

- [ ] API 엔드포인트 문서화
- [ ] 환경변수 설정 가이드
- [ ] Neo4j 스키마 문서

---

## 📎 Phase 2 예고

Phase 1 완료 후, Phase 2에서는 다음을 구현합니다:

- Entity Extraction (Haiku 기반)
- Hybrid Search (Vector + BM25 + Graph)
- Cross-Encoder Reranker
- Context Compression

→ `AI_ANALYSIS_v4.3_PHASE2.md` 참조

---

*Phase 1 - Foundation*
*v1.0.0 - 2025-12-13*