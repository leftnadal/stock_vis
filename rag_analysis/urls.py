from django.urls import path
from .views import (
    # DataBasket Views
    DataBasketListCreateView,
    DataBasketDetailView,
    DataBasketAddItemView,
    DataBasketAddStockDataView,
    DataBasketRemoveItemView,
    DataBasketClearView,
    # AnalysisSession Views
    AnalysisSessionListCreateView,
    AnalysisSessionDetailView,
    SessionMessagesView,
    ChatStreamView,
    # Monitoring Views
    UsageStatsView,
    CostSummaryView,
    CacheStatsView,
    UsageHistoryView,
    ModelPricingView,
)

app_name = 'rag_analysis'

urlpatterns = [
    # ============ DataBasket Endpoints ============

    # 바구니 목록/생성
    path('baskets/', DataBasketListCreateView.as_view(), name='basket-list-create'),

    # 바구니 상세/수정/삭제
    path('baskets/<int:pk>/', DataBasketDetailView.as_view(), name='basket-detail'),

    # 바구니 아이템 추가
    path('baskets/<int:pk>/add-item/', DataBasketAddItemView.as_view(), name='basket-add-item'),

    # 바구니에 주식 데이터 추가 (데이터 타입 선택)
    path('baskets/<int:pk>/add-stock-data/', DataBasketAddStockDataView.as_view(), name='basket-add-stock-data'),

    # 바구니 아이템 제거
    path('baskets/<int:pk>/items/<int:item_id>/', DataBasketRemoveItemView.as_view(), name='basket-remove-item'),

    # 바구니 비우기
    path('baskets/<int:pk>/clear/', DataBasketClearView.as_view(), name='basket-clear'),


    # ============ AnalysisSession Endpoints ============

    # 세션 목록/생성
    path('sessions/', AnalysisSessionListCreateView.as_view(), name='session-list-create'),

    # 세션 상세/삭제
    path('sessions/<int:pk>/', AnalysisSessionDetailView.as_view(), name='session-detail'),

    # 세션 메시지 목록
    path('sessions/<int:pk>/messages/', SessionMessagesView.as_view(), name='session-messages'),

    # 채팅 스트리밍 (SSE)
    path('sessions/<int:pk>/chat/stream/', ChatStreamView.as_view(), name='chat-stream'),


    # ============ Monitoring Endpoints ============

    # 사용량 통계
    path('monitoring/usage/', UsageStatsView.as_view(), name='monitoring-usage'),

    # 비용 요약
    path('monitoring/cost/', CostSummaryView.as_view(), name='monitoring-cost'),

    # 캐시 통계
    path('monitoring/cache/', CacheStatsView.as_view(), name='monitoring-cache'),

    # 사용량 히스토리
    path('monitoring/history/', UsageHistoryView.as_view(), name='monitoring-history'),

    # 모델 가격 정보
    path('monitoring/pricing/', ModelPricingView.as_view(), name='monitoring-pricing'),
]
