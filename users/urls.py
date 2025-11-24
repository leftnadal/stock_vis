from django.urls import path
from . import views, jwt_views
from rest_framework_simplejwt.views import TokenRefreshView

app_name = 'users'

urlpatterns = [
    # JWT 인증 관련
    path('jwt/signup/', jwt_views.JWTSignUpView.as_view(), name='jwt-signup'),
    path('jwt/login/', jwt_views.CustomTokenObtainPairView.as_view(), name='jwt-login'),
    path('jwt/logout/', jwt_views.JWTLogoutView.as_view(), name='jwt-logout'),
    path('jwt/refresh/', TokenRefreshView.as_view(), name='jwt-refresh'),
    path('jwt/verify/', jwt_views.JWTVerifyView.as_view(), name='jwt-verify'),
    path('jwt/change-password/', jwt_views.ChangePasswordJWTView.as_view(), name='jwt-change-password'),
    path('jwt/profile/', jwt_views.ProfileUpdateView.as_view(), name='jwt-profile'),

    # 기존 세션 기반 인증 (하위 호환성)
    path('me/', views.Me.as_view(), name='me'),
    path('', views.Users.as_view(), name='users'),
    path('@<str:user_name>/', views.PublicUser.as_view(), name='public_user'),
    path('change_password/', views.ChangePassword.as_view(), name='change_password'),
    path('login/', views.LogIn.as_view(), name='login'),
    path('logout/', views.LogOut.as_view(), name='logout'),

    # 즐겨찾기 관련
    path('favorites/', views.UserFavorites.as_view(), name='favorites'),
    path('favorites/add/<int:stock_id>/', views.AddFavorite.as_view(), name='add_favorite'),
    path('favorites/remove/<int:stock_id>/', views.RemoveFavorite.as_view(), name='remove_favorite'),

    # 포트폴리오 관련
    path('portfolio/', views.PortfolioListCreateView.as_view(), name='portfolio-list'),
    path('portfolio/summary/', views.PortfolioSummaryView.as_view(), name='portfolio-summary'),
    path('portfolio/table/', views.PortfolioDetailTableView.as_view(), name='portfolio-table'),
    path('portfolio/refresh/', views.RefreshPortfolioDataView.as_view(), name='portfolio-refresh'),
    path('portfolio/<int:pk>/', views.PortfolioDetailView.as_view(), name='portfolio-detail'),
    path('portfolio/<int:pk>/quick-update/', views.PortfolioDetailTableView.as_view(), name='portfolio-quick-update'),
    path('portfolio/symbol/<str:symbol>/', views.PortfolioBySymbolView.as_view(), name='portfolio-by-symbol'),
    path('portfolio/symbol/<str:symbol>/refresh/', views.RefreshStockDataView.as_view(), name='stock-refresh'),
    path('portfolio/symbol/<str:symbol>/status/', views.StockDataStatusView.as_view(), name='stock-data-status'),
]