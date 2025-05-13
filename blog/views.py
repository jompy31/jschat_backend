from rest_framework import generics, permissions
from rest_framework.permissions import AllowAny
from .models import BlogPost, Comment, Like
from .serializers import BlogPostSerializer, CommentSerializer, LikeSerializer
from django.db.models import Prefetch
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticatedOrReadOnly

class BlogPostListCreate(generics.ListCreateAPIView):
    serializer_class = BlogPostSerializer
    queryset = BlogPost.objects.all()
    permission_classes = [AllowAny] # Permitir acceso sin autenticación

    def perform_create(self, serializer):
        author = self.request.user
        image = self.request.data.get('image')

        serializer.save(author=author, image=image)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.user.is_authenticated:
            context['user'] = self.request.user
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.prefetch_related(Prefetch('likes', queryset=Like.objects.select_related('user')))
        return queryset

class BlogPostRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BlogPostSerializer
    queryset = BlogPost.objects.all()
    permission_classes = [AllowAny]  


class CommentListCreate(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        blog_post_id = self.kwargs['blog_post_id']
        return Comment.objects.filter(blog_post_id=blog_post_id).order_by('-created_at')

    def perform_create(self, serializer):
        blog_post_id = self.kwargs['blog_post_id']
        blog_post = BlogPost.objects.get(id=blog_post_id)
        serializer.save(blog_post=blog_post, user=self.request.user)


class CommentRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CommentSerializer
    permission_classes = [AllowAny]  

    def get_queryset(self):
        blog_post_id = self.kwargs['blog_post_id']
        return Comment.objects.filter(blog_post_id=blog_post_id)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LikeCreate(generics.CreateAPIView):
    serializer_class = LikeSerializer
    permission_classes = [AllowAny]  

    def perform_create(self, serializer):
        blog_post_id = self.kwargs['blog_post_id']
        blog_post = BlogPost.objects.get(id=blog_post_id)
        user = self.request.user

        # Verificar si el like ya existe
        existing_like = Like.objects.filter(blog_post=blog_post, user=user).first()

        if existing_like:
            # El like ya existe, eliminarlo
            existing_like.delete()
        else:
            # El like no existe, crearlo
            like = serializer.save(blog_post=blog_post, user=user)

            # Obtén la lista actualizada de usuarios a los que les gusta la publicación
            liked_users = blog_post.likes.all().values('user__username')
            like.likedUsers = liked_users

            return like
