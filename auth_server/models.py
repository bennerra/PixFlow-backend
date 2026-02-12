import jwt
from datetime import datetime, timedelta

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