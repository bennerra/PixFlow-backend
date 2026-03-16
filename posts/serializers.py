from rest_framework import serializers

from posts.models import Post

class PostListSerializer(serializers.ModelSerializer):
    likes_count = serializers.IntegerField(read_only=True)
    short_url = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

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

    class Meta:
        model = Post
        fields = ['id', 'name', 'likes_count', 'short_url', 'is_liked']

class PostDetailSerializer(serializers.ModelSerializer):
    likes_count = serializers.IntegerField(read_only=True)
    short_url = serializers.SerializerMethodField()
    author_name = serializers.CharField(source='author.username', read_only=True)
    author_id = serializers.CharField(source='author.id', read_only=True)
    is_liked = serializers.SerializerMethodField()

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

    class Meta:
        model = Post
        fields = ['id', 'name', 'likes_count', 'short_url', 'description', 'author_name', 'author_id', 'is_liked']

class PostCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['name', 'description', 'image']

    def validate_image(self, value):
        if value:
            import os

            ext = os.path.splitext(value.name)[1].lower()
            allowed_extensions = ['.jpg', '.jpeg', '.gif', '.png', '.webp', '.bpm', '.svg']
            if ext not in allowed_extensions:
                raise serializers.ValidationError(f"Поддерживаются только форматы: {', '.join(allowed_extensions)}")

        return value

    def validate(self, data):
        if not data.get('name'):
            raise serializers.ValidationError('Поле name обязательное')

        if not data.get('image'):
            raise serializers.ValidationError('Поле image обязательное')

        return data