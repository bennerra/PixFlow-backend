import pytest
from django.contrib.auth import get_user_model
from posts.models import Post, Like

User = get_user_model()

@pytest.mark.django_db
class TestLikeModel:
    """Тесты для модели Like"""

    @pytest.fixture
    def users(self):
        """Фикстура для создания тестовых пользователей"""
        user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            name='User One',
            password='testpass123'
        )
        user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            name='User Two',
            password='testpass123'
        )
        return user1, user2

    @pytest.fixture
    def post(self, users):
        """Фикстура для создания тестового поста"""
        user1, _ = users
        return Post.objects.create(
            name='Тестовый пост',
            description='Описание тестового поста',
            author=user1
        )

    def test_cascade_delete_on_user(self, users, post):
        """Тест каскадного удаления лайков при удалении пользователя"""
        user1, user2 = users

        # Создаем лайки от двух пользователей
        Like.objects.create(user=user1, post=post)
        Like.objects.create(user=user2, post=post)

        assert Like.objects.count() == 2

        # Удаляем одного пользователя
        user2.delete()

        # Должен остаться только лайк от user1
        assert Like.objects.count() == 1
        assert Like.objects.first().user == user1

    def test_cascade_delete_on_post(self, users, post):
        """Тест каскадного удаления лайков при удалении поста"""
        user1, user2 = users

        # Создаем лайки от двух пользователей
        Like.objects.create(user=user1, post=post)
        Like.objects.create(user=user2, post=post)

        assert Like.objects.count() == 2

        # Удаляем пост
        post_id = post.id
        post.delete()

        # Все лайки должны удалиться
        assert Like.objects.count() == 0
        assert not Post.objects.filter(id=post_id).exists()

    def test_likes_count_property(self, users, post):
        """Тест свойства likes_count у модели Post"""
        user1, user2 = users

        # Изначально лайков нет
        assert post.likes_count == 0

        # Добавляем лайк от первого пользователя
        Like.objects.create(user=user1, post=post)
        assert post.likes_count == 1

        # Добавляем лайк от второго пользователя
        Like.objects.create(user=user2, post=post)
        assert post.likes_count == 2

        # Удаляем лайк первого пользователя
        Like.objects.filter(user=user1, post=post).delete()
        assert post.likes_count == 1