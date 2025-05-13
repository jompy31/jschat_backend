from django.urls import path
from . import views

urlpatterns = [
    path('posts/', views.BlogPostListCreate.as_view()),
    path('posts/<int:pk>/', views.BlogPostRetrieveUpdateDestroy.as_view()),
    path('posts/<int:blog_post_id>/comments/', views.CommentListCreate.as_view()),
    path('posts/<int:blog_post_id>/comments/<int:pk>/', views.CommentRetrieveUpdateDestroy.as_view()),
    path('posts/<int:blog_post_id>/likes/', views.LikeCreate.as_view()),
]
