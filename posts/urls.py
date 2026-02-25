from django.urls import path

from posts import views

name = 'posts'

urlpatterns = [
    path('posts/', views.PostViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('posts/<int:pk>', views.PostViewSet.as_view({'get': 'retrieve'})),
    path('my_posts/', views.PostViewSet.as_view({'get': 'my_posts'})),
]
