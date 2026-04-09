from django.urls import path

from posts import views

name = 'posts'

urlpatterns = [
    path('posts/', views.PostViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('posts/<int:pk>/', views.PostViewSet.as_view({'get': 'retrieve'})),
    path('my_posts/', views.PostViewSet.as_view({'get': 'my_posts'})),
    path('user_posts/<int:pk>/', views.PostViewSet.as_view({'get': 'user_posts'})),
    path('posts/like/<int:pk>/', views.PostViewSet.as_view({'post': 'like'})),
    path('posts/save/<int:pk>/', views.PostViewSet.as_view({'post': 'save'})),
    path('saved_posts/', views.PostViewSet.as_view({'get': 'saved_posts'})),
    path('saved_posts/<int:user_id>/', views.PostViewSet.as_view({'get': 'saved_posts'})),
]
