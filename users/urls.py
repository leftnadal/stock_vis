##1차 작성중..
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('me/', views.Me.as_view(), name='me'),
    path('', views.Users.as_view(), name='users'),
    path('@<str:user_name>/', views.PublicUser.as_view(), name='public_user'),
    path('change_password/', views.ChangePassword.as_view(), name='change_password'),
    path('login/', views.LogIn.as_view(), name='login'),
    path('logout/', views.LogOut.as_view(), name='logout'),
    path('favorites/', views.UserFavorites.as_view(), name='favorites'),
    path('favorites/add/<int:stock_id>/', views.AddFavorite.as_view(), name='add_favorite'),
    path('favorites/remove/<int:stock_id>/', views.RemoveFavorite.as_view(), name='remove_favorite'),
]