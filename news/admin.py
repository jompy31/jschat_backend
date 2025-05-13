from django.contrib import admin
from .models import Category, Article, Comment, Subscription

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    
@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'publication_date', 'category', 'status')
    search_fields = ('title', 'author__username', 'category__name')
    list_filter = ('status', 'category')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'likes')
    search_fields = ('user__username', 'article__title')

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'notification_preference')
    search_fields = ('user__username', 'category__name')
