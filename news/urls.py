##1차 작성중
from django.urls import path
from . import views

app_name = 'news'

urlpatterns = [
    path('', views.NewsList.as_view(), name='news_list'),
    path('<int:pk>/', views.NewsDetail.as_view(), name='news_detail'),
    path('stock/<int:stock_id>/', views.StockNews.as_view(), name='stock_news'),
    path('latest/', views.LatestNews.as_view(), name='latest_news'),
]