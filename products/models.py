from django.db import models
from django.contrib.auth.models import User
import os

class ProductType(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_time_days = models.PositiveIntegerField()
    daily_production_capacity = models.PositiveIntegerField(default=100)  # New field
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_product_types'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Characteristic(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name

class Product(models.Model):
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    design_file = models.FileField(upload_to='product_designs/', blank=True, null=True)
    additional_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    characteristics = models.ManyToManyField(Characteristic, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_products'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.product_type.name})"
    
    def delete(self, *args, **kwargs):
        if self.design_file and os.path.isfile(self.design_file.path):
            os.remove(self.design_file.path)
        super().delete(*args, **kwargs)