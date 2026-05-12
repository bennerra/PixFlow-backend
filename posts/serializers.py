from rest_framework import serializers

from auth_server.models import SubscriptionRequest, Subscription, User
from posts.models import Post, Comment

class PostListSerializer(serializers.ModelSerializer):
    likes_count = serializers.IntegerField(read_only=True)
    short_url = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    saves_count = serializers.IntegerField(source='saves.count', read_only=True)
    is_saved = serializers.SerializerMethodField()

    def get_likes(self, obj):
        return obj.likes.count()

    def get_short_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url)
        return None

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.saves.filter(user=request.user).exists()
        return False

    class Meta:
        model = Post
        fields = ['id', 'name', 'likes_count', 'short_url', 'is_liked', 'saves_count', 'is_saved']

class PostDetailSerializer(serializers.ModelSerializer):
    likes_count = serializers.IntegerField(read_only=True)
    short_url = serializers.SerializerMethodField()
    author_name = serializers.CharField(source='author.username', read_only=True)
    author_id = serializers.CharField(source='author.id', read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()

    def get_likes(self, obj):
        return obj.likes.count()

    def get_short_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url)
        return None

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.saves.filter(user=request.user).exists()
        return False

    class Meta:
        model = Post
        fields = ['id', 'name', 'likes_count', 'short_url', 'description', 'author_name', 'author_id', 'is_liked', 'is_saved']

class PostCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['name', 'description', 'image']

    def validate_image(self, value):
        if value:
            import os

            ext = os.path.splitext(value.name)[1].lower()
            allowed_extensions = ['.jpg', '.jpeg', '.gif', '.png', '.webp', '.bmp', '.svg']
            if ext not in allowed_extensions:
                raise serializers.ValidationError(f"Поддерживаются только форматы: {', '.join(allowed_extensions)}")

        return value

    def validate(self, data):
        if not data.get('name'):
            raise serializers.ValidationError('Поле name обязательное')

        if not data.get('image'):
            raise serializers.ValidationError('Поле image обязательное')

        return data


class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='user.username', read_only=True)
    author_id = serializers.CharField(source='user.id', read_only=True)
    author_avatar = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'text', 'created_at',
            'author_name', 'author_id', 'author_avatar'
        ]
        read_only_fields = ['id', 'created_at']

    def get_author_avatar(self, obj):
        if hasattr(obj.user, 'avatar') and obj.user.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user.avatar.url)
        return None


class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['text', 'post']

    def validate_text(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Комментарий не может быть пустым")
        return value.strip()

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class FollowerSerializer(serializers.ModelSerializer):
    """Сериализатор для подписчиков"""
    username = serializers.CharField(source='follower.username', read_only=True)
    avatar = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    followed_at = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Subscription
        fields = ['id', 'username', 'avatar', 'full_name', 'followed_at']

    def get_avatar(self, obj):
        if hasattr(obj.follower, 'avatar') and obj.follower.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.follower.avatar.url)
        return None

    def get_full_name(self, obj):
        return f"{obj.follower.first_name} {obj.follower.last_name}".strip() or obj.follower.username


class FollowingSerializer(serializers.ModelSerializer):
    """Сериализатор для подписок"""
    username = serializers.CharField(source='following.username', read_only=True)
    avatar = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    followed_at = serializers.DateTimeField(source='created_at', read_only=True)
    is_subscribed_back = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = ['id', 'username', 'avatar', 'full_name', 'followed_at', 'is_subscribed_back']

    def get_avatar(self, obj):
        if hasattr(obj.following, 'avatar') and obj.following.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.following.avatar.url)
        return None

    def get_full_name(self, obj):
        return f"{obj.following.first_name} {obj.following.last_name}".strip() or obj.following.username

    def get_is_subscribed_back(self, obj):
        """Подписан ли автор ответно на текущего пользователя"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                follower=obj.following,
                following=request.user,
                is_active=True
            ).exists()
        return False


class UserProfileSerializer(serializers.ModelSerializer):
    """Сериализатор профиля пользователя с информацией о подписках"""
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    is_followed_by_user = serializers.SerializerMethodField()
    subscription_status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'avatar', 'bio', 'followers_count', 'following_count',
            'is_following', 'is_followed_by_user', 'subscription_status'
        ]

    def get_followers_count(self, obj):
        return obj.followers.filter(is_active=True).count()

    def get_following_count(self, obj):
        return obj.following.filter(is_active=True).count()

    def get_is_following(self, obj):
        """Подписан ли текущий пользователь на этого пользователя"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                follower=request.user,
                following=obj,
                is_active=True
            ).exists()
        return False

    def get_is_followed_by_user(self, obj):
        """Подписан ли этот пользователь на текущего"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                follower=obj,
                following=request.user,
                is_active=True
            ).exists()
        return False

    def get_subscription_status(self, obj):
        """Статус подписки (для закрытых аккаунтов)"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Проверяем статус запроса на подписку
            try:
                subscription_request = SubscriptionRequest.objects.get(
                    follower=request.user,
                    following=obj
                )
                return subscription_request.status
            except SubscriptionRequest.DoesNotExist:
                pass
        return None


class SubscriptionActionSerializer(serializers.Serializer):
    """Сериализатор для действия подписки"""
    user_id = serializers.IntegerField(required=True)

    def validate_user_id(self, value):
        if value == self.context['request'].user.id:
            raise serializers.ValidationError("Нельзя подписаться на самого себя")
        return value


class SubscriptionRequestSerializer(serializers.ModelSerializer):
    """Сериализатор для запроса на подписку"""
    follower_username = serializers.CharField(source='follower.username', read_only=True)
    following_username = serializers.CharField(source='following.username', read_only=True)

    class Meta:
        model = SubscriptionRequest
        fields = ['id', 'follower', 'following', 'follower_username', 'following_username',
                  'status', 'message', 'created_at']
        read_only_fields = ['created_at', 'updated_at']