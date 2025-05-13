from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class Property(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='affiliated_properties')
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=500)
    country = models.CharField(max_length=100,null=True, blank=True) 
    province = models.CharField(max_length=100,null=True, blank=True)   
    canton = models.CharField(max_length=100,null=True, blank=True)  
    rating = models.IntegerField(null=True, blank=True)
    pictures = models.ImageField(null=True, blank=True, upload_to="images/")
    
    def __str__(self):
        return self.title


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='affiliated_reviews')
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True, blank=True
    )
    comment = models.TextField()
    createdAt = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.property.title} by {self.user.username}"
