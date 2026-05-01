from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

from auth_server.models import Subscription

User = get_user_model()

class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ('id', 'username', 'name', 'email', 'password')
        read_only_fields = ('id',)
        extra_kwargs = {
            'name': {'required': True},
            'username': {'required': True, 'validators': [
                UniqueValidator(
                    queryset=User.objects.all(),
                    message="Пользователь с таким username уже существует."
                )
            ]},
            'email': {'required': True, 'validators': [
                UniqueValidator(
                    queryset=User.objects.all(),
                    message="Пользователь с такой почтой уже существует."
                )
            ]}
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Пользователь с таким именем пользователя уже существует")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            name=validated_data['name'],
            password=validated_data['password']
        )

        return user


class ProfileSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    date_birth = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()

    def get_date_birth(self, obj):
        if obj.date_birth:
            return obj.date_birth.strftime('%Y-%m-%d')
        return None

    def get_avatar(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None

    def get_is_following(self, obj):
        request = self.context.get('request')

        if not request or not request.user.is_authenticated:
            return False

        if request.user == obj:
            return False

        return Subscription.objects.filter(
            follower=request.user,
            following=obj,
            is_active=True
        ).exists()

    def get_followers_count(self, obj):
        return obj.followers.filter(is_active=True).count()

    def get_following_count(self, obj):
        return obj.following.filter(is_active=True).count()

    class Meta:
        model = User
        fields = ('id', 'username', 'name', 'email', 'avatar', 'date_birth', 'is_following', 'followers_count',
                  'following_count')


class ProfileUpdateSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        required=False,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message="Пользователь с таким username уже существует."
            )
        ]
    )
    email = serializers.EmailField(
        required=False,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message="Пользователь с такой почтой уже существует."
            )
        ]
    )
    old_password = serializers.CharField(
        write_only=True,
        required=False,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        write_only=True,
        required=False,
        validators=[validate_password],
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ('username', 'name', 'email', 'avatar', 'date_birth', 'old_password', 'new_password')
        extra_kwargs = {
            'name': {'required': False},
            'avatar': {'required': False},
            'date_birth': {'required': False},
        }

    def validate_username(self, value):
        if value and self.instance.username != value:
            if User.objects.filter(username=value).exists():
                raise serializers.ValidationError("Пользователь с таким именем пользователя уже существует")
        return value

    def validate_email(self, value):
        if value and self.instance.email != value:
            if User.objects.filter(email=value).exists():
                raise serializers.ValidationError("Пользователь с такой почтой уже существует")
        return value

    def validate_old_password(self, value):
        if value and not self.instance.check_password(value):
            raise serializers.ValidationError("Неверный старый пароль")
        return value

    def validate(self, data):
        if data.get('new_password') and not data.get('old_password'):
            raise serializers.ValidationError({
                'old_password': 'Для смены пароля необходимо указать старый пароль'
            })

        if data.get('old_password') and not data.get('new_password'):
            raise serializers.ValidationError({
                'new_password': 'Введите новый пароль'
            })

        return data

    def update(self, instance, validated_data):
        instance.username = validated_data.get('username', instance.username)
        instance.name = validated_data.get('name', instance.name)
        instance.email = validated_data.get('email', instance.email)
        instance.avatar = validated_data.get('avatar', instance.avatar)
        instance.date_birth = validated_data.get('date_birth', instance.date_birth)

        if validated_data.get('new_password'):
            instance.set_password(validated_data['new_password'])

        instance.save()
        return instance


class ProfileUpdateView(APIView):
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