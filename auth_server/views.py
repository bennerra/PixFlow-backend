from rest_framework.permissions import IsAuthenticated
import requests
from auth_server.models import User, Subscription, SubscriptionRequest
from auth_server.serializers import CustomUserSerializer, ProfileSerializer, ProfileUpdateSerializer, VKOAuthSerializer
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework import status, permissions, viewsets
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.generics import UpdateAPIView

from django.utils import timezone
from datetime import timedelta

from posts.serializers import SubscriptionActionSerializer, FollowerSerializer, FollowingSerializer, SubscriptionRequestSerializer
from settings import settings


class VKOAuthView(APIView):
    """Обработка авторизации через VK ID"""
    permission_classes = []
    serializer_class = VKOAuthSerializer

    def post(self, request):
        serializer = VKOAuthSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        code = serializer.validated_data['code']
        device_id = serializer.validated_data['device_id']
        print(device_id)
        try:
            # 1. Обмениваем code на access_token
            token_url = 'https://id.vk.com/oauth2/auth'
            token_params = {
                'grant_type': 'authorization_code',
                'state': "01234567890123456789012345678912",
                'code_verifier': 'dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk',
                'device_id': device_id,
                'client_id': settings.VK_CLIENT_ID,
                'client_secret': settings.VK_CLIENT_SECRET,
                'redirect_uri': settings.VK_REDIRECT_URI,
                'code': code,
            }

            response = requests.post(token_url, data=token_params)
            response.raise_for_status()
            token_data = response.json()

            # 2. Получаем данные пользователя
            access_token = token_data.get('access_token')
            user_id = token_data.get('user_id')
            email = token_data.get('email')

            if not access_token or not user_id:
                return Response(
                    {'error': 'Не удалось получить токен или ID пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 3. Получаем информацию о пользователе
            user_info_url = 'https://api.vk.com/method/users.get'
            user_info_params = {
                'access_token': access_token,
                'user_ids': user_id,
                'fields': 'first_name,last_name,photo_100',
                'v': settings.VK_API_VERSION
            }

            user_info_response = requests.get(user_info_url, params=user_info_params)
            user_info_response.raise_for_status()
            user_info_data = user_info_response.json()

            if 'error' in user_info_data:
                return Response(
                    {'error': user_info_data['error'].get('error_msg', 'Ошибка получения данных пользователя')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            vk_user = user_info_data['response'][0]
            vk_id = str(user_id)

            # 4. Ищем или создаем пользователя в БД
            user = self.get_or_create_user(
                vk_id=vk_id,
                email=email,
                first_name=vk_user.get('first_name', ''),
                last_name=vk_user.get('last_name', ''),
                avatar_url=vk_user.get('photo_100', '')
            )

            # 5. Генерируем JWT токены
            refresh = RefreshToken.for_user(user)
            refresh.payload.update({
                'user_id': user.id,
                'username': user.username
            })

            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'name': user.name
                }
            }, status=status.HTTP_200_OK)

        except requests.exceptions.RequestException as e:
            return Response(
                {'error': f'Ошибка при обращении к VK API: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Внутренняя ошибка сервера: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_or_create_user(self, vk_id, email, first_name, last_name, avatar_url):
        """Создает или обновляет пользователя на основе данных из VK"""

        # Генерируем username на основе VK ID
        username = f"vk_{vk_id}"
        name = f"{first_name} {last_name}".strip() or "Пользователь VK"

        # Ищем пользователя по email или username
        user = None
        if email:
            user = User.objects.filter(email=email).first()

        if not user:
            user = User.objects.filter(username=username).first()

        if user:
            # Обновляем существующего пользователя
            user.name = name
            if not user.avatar and avatar_url:
                # Здесь можно скачать аватар с VK и сохранить локально
                pass
            user.save()
        else:
            # Создаем нового пользователя
            user = User.objects.create_user(
                username=username,
                email=email or f"{vk_id}@vk.user",
                name=name,
                password=None  # Пользователи через VK входят без пароля
            )

        return user

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
                'access': str(refresh.access_token),
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

    def get(self, request, username):
        user = get_object_or_404(User, username=username)
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

        user_identifier = serializer.validated_data['user_identifier']

        try:
            user_id = int(user_identifier)
            following_user = User.objects.get(id=user_id)
        except (ValueError, User.DoesNotExist):
            try:
                following_user = User.objects.get(username=user_identifier)
            except User.DoesNotExist:
                return Response({
                    'error': 'Пользователь не найден'
                }, status=status.HTTP_404_NOT_FOUND)

        subscription, created = Subscription.objects.get_or_create(
            follower=request.user,
            following=following_user,
            defaults={'is_active': True}
        )

        if not created and not subscription.is_active:
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

        user_identifier = serializer.validated_data['user_identifier']

        try:
            user_id = int(user_identifier)
            following_user = User.objects.get(id=user_id)
        except (ValueError, User.DoesNotExist):
            try:
                following_user = User.objects.get(username=user_identifier)
            except User.DoesNotExist:
                return Response({
                    'error': 'Пользователь не найден'
                }, status=status.HTTP_404_NOT_FOUND)

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
        user_identifier = request.query_params.get('user_identifier')

        if user_identifier:
            try:
                user = User.objects.get(id=user_identifier)
            except User.DoesNotExist:
                try:
                    user = User.objects.get(username=user_identifier)
                except User.DoesNotExist:
                    return Response({
                        'error': 'Пользователь не найден'
                    }, status=status.HTTP_404_NOT_FOUND)
        else:
            user = request.user

        subscriptions = Subscription.objects.filter(
            following=user,
            is_active=True
        ).select_related('follower')

        page = self.paginate_queryset(subscriptions)
        if page is not None:
            serializer = FollowerSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = FollowerSerializer(subscriptions, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def following(self, request):
        """Получить список подписок текущего пользователя"""
        user_identifier = request.query_params.get('user_identifier')

        if user_identifier:
            try:
                user = User.objects.get(id=user_identifier)
            except User.DoesNotExist:
                try:
                    user = User.objects.get(username=user_identifier)
                except User.DoesNotExist:
                    return Response({
                        'error': 'Пользователь не найден'
                    }, status=status.HTTP_404_NOT_FOUND)
        else:
            user = request.user

        subscriptions = Subscription.objects.filter(
            follower=user,
            is_active=True
        ).select_related('following')

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

class PremiumSubscriptionViewSet(ViewSet):
    """ViewSet для управления премиум‑подписками"""
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'])
    def purchase(self, request):
        """Оформить премиум‑подписку с указанием срока"""
        user = request.user
        duration_months = request.data.get('duration_months', 1)

        valid_durations = [1, 3, 6, 12]
        if duration_months not in valid_durations:
            return Response({
                'error': f'Недопустимый срок. Доступные варианты: {valid_durations} месяцев'
            }, status=status.HTTP_400_BAD_REQUEST)

        if user.is_premium and user.premium_until:
            if user.premium_until > timezone.now():
                return Response({
                    'status': 'already_premium',
                    'message': f'У вас уже есть активная премиум‑подписка до {user.premium_until.strftime("%d.%m.%Y")}'
                }, status=status.HTTP_200_OK)

        premium_until = timezone.now() + timedelta(days=duration_months * 30)

        user.is_premium = True
        user.premium_until = premium_until
        user.save()

        return Response({
            'status': 'premium_purchased',
            'message': f'Премиум‑подписка на {duration_months} месяц(ев) успешно оформлена!',
            'premium_until': user.premium_until.isoformat(),
            'duration_months': duration_months
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def status(self, request):
        """Получить текущий статус премиум‑подписки"""
        user = request.user

        return Response({
            'is_premium': user.is_premium,
            'premium_until': user.premium_until.isoformat() if user.premium_until else None,
            'is_active': user.is_premium and (user.premium_until is None or user.premium_until > timezone.now())
        })

    @action(detail=False, methods=['post'])
    def cancel(self, request):
        """Отменить премиум‑подписку"""
        user = request.user

        if not user.is_premium:
            return Response({
                'status': 'not_premium',
                'message': 'У вас нет активной премиум‑подписки'
            }, status=status.HTTP_200_OK)

        user.is_premium = False
        user.premium_until = None
        user.save()

        return Response({
            'status': 'cancelled',
            'message': 'Премиум‑подписка успешно отменена'
        }, status=status.HTTP_200_OK)


class ProfileUpdateView(UpdateAPIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = ProfileUpdateSerializer

    def put(self, request):
        serializer = ProfileUpdateSerializer(
            instance=request.user,
            data=request.data,
            partial=False,
            context={'request': request}
        )

        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': 'Профиль успешно обновлен',
                'user': ProfileSerializer(user).data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            instance=request.user,
            data=request.data,
            partial=True,
            context={'request': request}
        )

        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': 'Профиль успешно обновлен',
                'user': ProfileSerializer(user).data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)