from django.db import models

# Create your models here.

class Post(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    short_url = models.CharField(max_length=100)

class Like(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)