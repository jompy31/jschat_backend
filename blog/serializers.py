from rest_framework import serializers
from .models import BlogPost, Comment, Like

class CommentSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    content = serializers.CharField(allow_blank=True)  # Actualización aquí

    class Meta:
        model = Comment
        fields = ['id', 'user', 'content', 'created_at']

class LikeSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Like
        fields = ['user']

class BlogPostSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.username')
    comments = CommentSerializer(many=True, read_only=True)
    likes = LikeSerializer(many=True, read_only=True)

    class Meta:
        model = BlogPost
        fields = ['id', 'author', 'title', 'content', 'image', 'created_at', 'comments', 'likes', 'comercial_activity']
