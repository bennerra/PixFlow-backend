from django.contrib import admin

from posts.models import Post, Save

# Register your models here.
admin.site.register(Post)
@admin.register(Save)
class SaveAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'post', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'post__name')
    readonly_fields = ('created_at',)