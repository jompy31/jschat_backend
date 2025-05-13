from django.urls import path
from .views import (
    CategoryListCreate,
    CategoryRetrieveUpdateDestroy,
    ArticleListCreate,
    ArticleRetrieveUpdateDestroy,
    CommentListCreate,
    CommentRetrieveUpdateDestroy,
    SubscriptionListCreate,
    SubscriptionRetrieveUpdateDestroy,
)

urlpatterns = [
    # Rutas para Category
    path('categories/', CategoryListCreate.as_view(), name='category-list-create'),
    path('categories/<int:pk>/', CategoryRetrieveUpdateDestroy.as_view(), name='category-detail'),

    # Rutas para Article
    path('articles/', ArticleListCreate.as_view(), name='article-list-create'),
    path('articles/<int:pk>/', ArticleRetrieveUpdateDestroy.as_view(), name='article-detail'),

    # Rutas para Comment
    path('comments/', CommentListCreate.as_view(), name='comment-list-create'),
    path('comments/<int:pk>/', CommentRetrieveUpdateDestroy.as_view(), name='comment-detail'),

    # Rutas para Subscription
    path('subscriptions/', SubscriptionListCreate.as_view(), name='subscription-list-create'),
    path('subscriptions/<int:pk>/', SubscriptionRetrieveUpdateDestroy.as_view(), name='subscription-detail'),
]
