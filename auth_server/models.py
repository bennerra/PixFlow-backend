from django.utils import timezone

import jwt

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import ( BaseUserManager, PermissionsMixin )
from django.db import models

# Create your models here.

class UserManager(BaseUserManager):
    def create_user(self, username, email, name, password=None):
        if username is None:
            raise TypeError('Users must have a username')

        if email is None:
            raise TypeError('Users must have a email')

        if name is None:
            raise TypeError('Users must have a name')

        user = self.model(username=username, email=self.normalize_email(email), name=name)
        user.set_password(password)
        user.save()

        return user

    def create_superuser(self, username, email, name, password=None):
        if password is None:
            raise TypeError('Superusers must have a password')

        if name is None:
            raise TypeError('Superusers must have a name')

        user = self.create_user(username, email, name, password)
        user.is_superuser = True
        user.is_staff = True
        user.save()

        return user

class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(db_index=True, max_length=255, unique=True)
    name = models.CharField(db_index=True, max_length=255)
    email = models.EmailField(db_index=True, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    date_birth = models.DateField(null=True, blank=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['name', 'email']

    objects = UserManager()

    class Meta:
        db_table = 'users'
        verbose_name = 'Пользователя'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email

    @property
    def get_full_name(self):
        return self.username

    def get_short_name(self):
        return self.username


class Subscription(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Подписчик'
    )

    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='followers',
        verbose_name='Автор'
    )

    created_at = models.DateTimeField(default=timezone.now, verbose_name='Дата подписки')

    is_active = models.BooleanField(default=True, verbose_name='Активна')

    notify_new_posts = models.BooleanField(default=True, verbose_name='Уведомлять о новых постах')

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        ordering = ['-created_at']
        unique_together = ['follower', 'following']
        indexes = [
            models.Index(fields=['follower', '-created_at']),
            models.Index(fields=['following', '-created_at']),
            models.Index(fields=['follower', 'is_active']),
        ]

    def __str__(self):
        return f'{self.follower.username} подписан на {self.following.username}'

    def save(self, *args, **kwargs):
        if self.follower == self.following:
            raise ValueError("Нельзя подписаться на самого себя")
        super().save(*args, **kwargs)


class SubscriptionRequest(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription_requests_sent',
        verbose_name='Подписчик'
    )

    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription_requests_received',
        verbose_name='Автор'
    )

    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('approved', 'Одобрена'),
        ('rejected', 'Отклонена'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )

    message = models.TextField(
        blank=True,
        max_length=500,
        verbose_name='Сообщение'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Запрос на подписку'
        verbose_name_plural = 'Запросы на подписку'
        unique_together = ['follower', 'following']

    def __str__(self):
        return f'Запрос от {self.follower.username} к {self.following.username}'