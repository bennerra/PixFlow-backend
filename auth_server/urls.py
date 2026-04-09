from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from auth_server.serializers import ProfileUpdateView
from auth_server.views import RegistrationAPIView, LoginAPIView, LogoutAPIView, ProfileView, PublicUserDetailView

app_name = 'auth_server'

urlpatterns = [
    path('token/create/', RegistrationAPIView.as_view(), name='token_create'),
    path('token/', LoginAPIView.as_view(), name='token'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/me/', ProfileView.as_view(), name='users_me'),
    path('users/<int:pk>/', PublicUserDetailView.as_view(), name='users_profile'),
    path('users/update/', ProfileUpdateView.as_view(), name='profile-update'),
]
