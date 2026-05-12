from django.db import models
from django.urls import reverse
from django.conf import settings
from django.core.validators import MinLengthValidator, MaxLengthValidator

from auth_server.models import User

# Create your models here.
class Like(models.Model):
    user = models.ForeignKey('auth_server.User', on_delete=models.CASCADE, related_name='likes')
    post = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

class Post(models.Model):
    name = models.CharField(max_length=100, verbose_name='Наименование')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    image = models.FileField(upload_to='media/', null=True, blank=True, verbose_name='Изображение')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name='Автор'
    )

    class Meta:
        db_table = 'posts'
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'

    def __str__(self):
        return self.name

    @property
    def likes_count(self):
        return self.likes.count()

    def get_absolute_url(self):
        return reverse('post-detail', kwargs={'pk': self.pk})

    def get_short_url(self):
        return self.pk

class Save(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saves'
    )
    post = models.ForeignKey(
        'Post',
        on_delete=models.CASCADE,
        related_name='saves'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')
        ordering = ['-created_at']
        verbose_name = 'Сохраненный пост'
        verbose_name_plural = 'Сохраненные посты'

    def __str__(self):
        return f"{self.user.username} saved {self.post.name}"

class Comment(models.Model):
    text = models.TextField(validators=[
        MinLengthValidator(1, message='Комментарий не может быть пустым'),
        MaxLengthValidator(2000, message='Комментарий не может превышать 2000 символов')
    ], verbose_name='Текст комментария')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    post = models.ForeignKey(
        'Post',
        on_delete=models.CASCADE,
        related_name='comments'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['post', '-created_at']),
            models.Index(fields=['user', '-created_at'])
        ]

    def __str__(self):
        return f'Комментарий от {self.user} к {self.post}'