from rest_framework.permissions import IsAuthenticated

from auth_server.models import User, Subscription, SubscriptionRequest
from auth_server.serializers import CustomUserSerializer, ProfileSerializer
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework import status, permissions, viewsets
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action

from posts.serializers import SubscriptionActionSerializer, FollowerSerializer, FollowingSerializer, \
    SubscriptionRequestSerializer


class RegistrationAPIView(APIView):
    def post(self, request):
        serializer = CustomUserSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            refresh.payload.update({
                'user_id': user.id,
                'username': user.username
            })

            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),  # Отправка на клиент
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    def post(self, request):
        data = request.data
        username = data.get('username', None)
        password = data.get('password', None)
        if username is None or password is None:
            return Response({'error': 'Нужен и логин, и пароль'},
                            status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username, password=password)
        if user is None:
            return Response({'error': 'Неверные данные'},
                            status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)

        refresh.payload.update({
            'user_id': user.id,
            'username': user.username
        })

        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)


class LogoutAPIView(APIView):
    def post(self, request):
        refresh_token = request.data.get('refresh_token')  # С клиента нужно отправить refresh token

        if not refresh_token:
            return Response({'error': 'Необходим Refresh token'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()  # Добавить его в чёрный список

        except Exception as e:
            return Response({'error': 'Неверный Refresh token'},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response({'success': 'Выход успешен'}, status=status.HTTP_200_OK)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    def get(self, request):
        user = request.user
        serializer = ProfileSerializer(user, context={'request': request})
        return Response(serializer.data)

class PublicUserDetailView(APIView):
    permission_classes = []
    serializer_class = ProfileSerializer

    def get(self, request, pk):
        user = get_object_or_404(User, id=pk)
        serializer = self.serializer_class(user, context={'request': request})
        return Response(serializer.data)


class SubscriptionViewSet(viewsets.GenericViewSet):
    """ViewSet для управления подписками"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SubscriptionActionSerializer

    @action(detail=False, methods=['post'])
    def follow(self, request):
        """Подписаться на пользователя"""
        serializer = SubscriptionActionSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data['user_id']
        following_user = get_object_or_404(User, id=user_id)

        # Проверяем, есть ли уже подписка
        subscription, created = Subscription.objects.get_or_create(
            follower=request.user,
            following=following_user,
            defaults={'is_active': True}
        )

        if not created and not subscription.is_active:
            # Реактивируем подписку
            subscription.is_active = True
            subscription.save()
            created = True

        if created:
            return Response({
                'status': 'subscribed',
                'message': f'Вы подписались на {following_user.username}'
            }, status=status.HTTP_201_CREATED)

        return Response({
            'status': 'already_subscribed',
            'message': 'Вы уже подписаны на этого пользователя'
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def unfollow(self, request):
        """Отписаться от пользователя"""
        serializer = SubscriptionActionSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data['user_id']
        following_user = get_object_or_404(User, id=user_id)

        try:
            subscription = Subscription.objects.get(
                follower=request.user,
                following=following_user,
                is_active=True
            )
            subscription.is_active = False
            subscription.save()

            return Response({
                'status': 'unsubscribed',
                'message': f'Вы отписались от {following_user.username}'
            }, status=status.HTTP_200_OK)
        except Subscription.DoesNotExist:
            return Response({
                'status': 'not_subscribed',
                'message': 'Вы не были подписаны на этого пользователя'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def followers(self, request):
        """Получить список подписчиков текущего пользователя"""
        user_id = request.query_params.get('user_id')

        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = request.user

        subscriptions = Subscription.objects.filter(
            following=user,
            is_active=True
        ).select_related('follower')

        # Пагинация
        page = self.paginate_queryset(subscriptions)
        if page is not None:
            serializer = FollowerSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = FollowerSerializer(subscriptions, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def following(self, request):
        """Получить список подписок текущего пользователя"""
        user_id = request.query_params.get('user_id')

        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = request.user

        subscriptions = Subscription.objects.filter(
            follower=user,
            is_active=True
        ).select_related('following')

        # Пагинация
        page = self.paginate_queryset(subscriptions)
        if page is not None:
            serializer = FollowingSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = FollowingSerializer(subscriptions, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Получить статистику подписок"""
        user_id = request.query_params.get('user_id')

        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = request.user

        followers_count = Subscription.objects.filter(following=user, is_active=True).count()
        following_count = Subscription.objects.filter(follower=user, is_active=True).count()

        return Response({
            'followers_count': followers_count,
            'following_count': following_count
        })

    @action(detail=False, methods=['get'])
    def feed(self, request):
        """Получить посты пользователей, на которых подписан"""
        following_users = Subscription.objects.filter(
            follower=request.user,
            is_active=True
        ).values_list('following', flat=True)

        from posts.models import Post
        from posts.serializers import PostListSerializer

        posts = Post.objects.filter(
            author_id__in=following_users
        ).order_by('-created_at')

        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = PostListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = PostListSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def request_subscription(self, request):
        """Отправить запрос на подписку (для закрытых аккаунтов)"""
        user_id = request.data.get('user_id')
        message = request.data.get('message', '')

        following_user = get_object_or_404(User, id=user_id)

        # Проверяем, не подписан ли уже
        if Subscription.objects.filter(follower=request.user, following=following_user).exists():
            return Response({
                'error': 'Вы уже подписаны на этого пользователя'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Создаем запрос
        subscription_request, created = SubscriptionRequest.objects.get_or_create(
            follower=request.user,
            following=following_user,
            defaults={'message': message}
        )

        if created:
            return Response({
                'status': 'request_sent',
                'message': f'Запрос на подписку отправлен пользователю {following_user.username}'
            }, status=status.HTTP_201_CREATED)

        return Response({
            'status': 'request_exists',
            'message': 'Запрос на подписку уже отправлен'
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def handle_request(self, request):
        """Одобрить/отклонить запрос на подписку"""
        request_id = request.data.get('request_id')
        action_type = request.data.get('action')

        subscription_request = get_object_or_404(
            SubscriptionRequest,
            id=request_id,
            following=request.user,
            status='pending'
        )

        if action_type == 'approve':
            # Создаем подписку
            Subscription.objects.create(
                follower=subscription_request.follower,
                following=subscription_request.following,
                is_active=True
            )
            subscription_request.status = 'approved'
            subscription_request.save()

            return Response({
                'status': 'approved',
                'message': 'Запрос на подписку одобрен'
            })

        elif action_type == 'reject':
            subscription_request.status = 'rejected'
            subscription_request.save()

            return Response({
                'status': 'rejected',
                'message': 'Запрос на подписку отклонен'
            })

        return Response({
            'error': 'Неверное действие'
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def pending_requests(self, request):
        """Получить ожидающие запросы на подписку"""
        requests = SubscriptionRequest.objects.filter(
            following=request.user,
            status='pending'
        ).select_related('follower')

        serializer = SubscriptionRequestSerializer(requests, many=True)
        return Response(serializer.data)