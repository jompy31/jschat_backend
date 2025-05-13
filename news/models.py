from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name

class Article(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    publication_date = models.DateField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    tags = models.CharField(max_length=255)
    image_url = models.URLField(max_length=200)
    views = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default='Draft')

    def __str__(self):
        return self.title

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='news_comments')
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    content = models.TextField()
    likes = models.IntegerField(default=0)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.article.title}"

class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    notification_preference = models.CharField(max_length=50, default='Daily')

    def __str__(self):
        return f"Subscription of {self.user.username} to {self.category.name}"
