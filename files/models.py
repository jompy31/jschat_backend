from django.db import models
from django.contrib.auth.models import User
import os

class File(models.Model):
    file = models.FileField(upload_to='files/')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        # Eliminar el archivo del sistema de archivos
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        
        super().delete(*args, **kwargs)

class NewsPost(models.Model):
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    subcategory = models.CharField(max_length=100, null=True, blank=True)
    subsubcategory = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    province = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField()
    content_type = models.CharField(max_length=100, choices=[
        ('clasificado', 'Clasificado'),
        ('clasificado_logo', 'Clasificado_logo'),
        ('clasificado_imagen', 'Clasificado_imagen')
    ], null=True, blank=True)
    content = models.FileField(upload_to='news_content/', null=True, blank=True)
    datetime = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    url = models.URLField(max_length=200, blank=True)

    def __str__(self):
        return self.title

class Service(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2,  null=True, blank=True, default=None)
    distributor = models.ForeignKey('Distributor', on_delete=models.CASCADE, null=True, blank=True, default=None)
    def __str__(self):
        return self.name

   
class Distributor(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    country = models.CharField(max_length=50, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    canton = models.CharField(max_length=50, blank=True, null=True)
    district = models.CharField(max_length=50, blank=True, null=True)
    country1 = models.CharField(max_length=250, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    contact_name = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    comercial_activity = models.CharField(max_length=100, blank=True, null=True, default='')
    website = models.TextField(max_length=200, blank=True, null=True)
    pay_method = models.CharField(max_length=50, blank=True, null=True)
    logo = models.ImageField(upload_to='distributor_logos/', null=True, blank=True)

    def __str__(self):
        return self.name


class Design(models.Model):
    name = models.CharField(max_length=255)
    customer = models.CharField(max_length=255, blank=True, null=True, default='')
    context = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    url = models.URLField(max_length=200, blank=True)
    image = models.ImageField(upload_to='design_images/', blank=True)

    def __str__(self):
        return self.name