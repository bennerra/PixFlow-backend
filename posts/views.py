from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models.functions import Lower

from auth_server.models import User
from posts.models import Post, Like, Save, Comment
from posts.serializers import PostListSerializer, PostDetailSerializer, PostCreateSerializer, CommentCreateSerializer, \
    CommentSerializer


class IsAuthenticatedForCreate(permissions.BasePermission):
    def has_permission(self, request, view):
        # Разрешаем GET, HEAD, OPTIONS всем
        if request.method in permissions.SAFE_METHODS:
            return True
        # Для остальных методов (POST, PUT, DELETE) проверяем аутентификацию
        return request.user and request.user.is_authenticated

# Create your views here.
class PostViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedForCreate]

    def get_serializer_class(self):
        if self.action == 'list':
            return PostListSerializer
        elif self.action == 'retrieve':
            return PostDetailSerializer
        elif self.action == 'create':
            return PostCreateSerializer
        elif self.action == 'my_posts':
            return PostListSerializer
        elif self.action == 'user_posts':
            return PostListSerializer
        elif self.action == 'saved_posts':
            return PostListSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = Post.objects.all().order_by('-created_at')

        search_value = self.request.query_params.get('searchValue', None)

        if search_value:
            queryset = queryset.annotate(
                name_lower=Lower('name')
            ).filter(name_lower__icontains=search_value.lower())

        return queryset

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticatedForCreate])
    def my_posts(self, request, *args, **kwargs):
        posts = Post.objects.filter(author=request.user).order_by('-created_at')
        page = self.paginate_queryset(posts)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(page, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticatedForCreate])
    def user_posts(self, request, pk=None):
        posts = Post.objects.filter(author=pk).order_by('-created_at')
        page = self.paginate_queryset(posts)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(page, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticatedForCreate])
    def like(self, request, pk=None):
        if not request.user or not request.user.is_authenticated:
            return Response(
                {"error": "Требуется авторизация"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        post = self.get_object()
        user = request.user

        like = Like.objects.filter(user=user, post=post).first()

        if like:
            like.delete()
            liked = False
        else:
            Like.objects.create(user=user, post=post)
            liked = True

        return Response({
            'id': post.id,
            'count': post.likes.count(),
            'is_liked': liked
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticatedForCreate])
    def save(self, request, pk=None):
        """Сохранение/удаление поста из сохраненных"""
        if not request.user or not request.user.is_authenticated:
            return Response(
                {"error": "Требуется авторизация"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        post = self.get_object()
        user = request.user

        # Проверяем, сохранен ли уже пост
        saved = Save.objects.filter(user=user, post=post).first()

        if saved:
            saved.delete()
            is_saved = False
        else:
            Save.objects.create(user=user, post=post)
            is_saved = True

        return Response({
            'id': post.id,
            'saves_count': post.saves.count(),
            'is_saved': is_saved
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticatedForCreate])
    def saved_posts(self, request, user_id=None, *args, **kwargs):
        """Получение сохраненных постов пользователя по ID"""
        target_user_id = user_id or request.user.id

        try:
            target_user = User.objects.get(id=target_user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "Пользователь не найден"},
                status=status.HTTP_404_NOT_FOUND
            )

        saved_post_ids = Save.objects.filter(
            user=target_user
        ).values_list('post_id', flat=True)

        posts = Post.objects.filter(
            id__in=saved_post_ids
        ).order_by('-created_at')

        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.action == 'create':
            return CommentCreateSerializer
        return CommentSerializer

    def get_queryset(self):
        queryset = Comment.objects.all()

        post_id = self.request.query_params.get('post_id')
        if post_id:
            queryset = queryset.filter(post_id=post_id)

        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()

        if comment.user != request.user and not request.user.is_staff:
            return Response(
                {'error': 'У вас нет прав на удаление этого комментария'},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().destroy(request, *args, **kwargs)