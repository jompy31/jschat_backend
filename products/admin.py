from django.contrib import admin
from .models import ProductType, Characteristic, Product

@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_price', 'delivery_time_days', 'daily_production_capacity', 'created_by')
    search_fields = ('name',)

@admin.register(Characteristic)
class CharacteristicAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_type', 'additional_price', 'created_by')
    list_filter = ('product_type',)
    search_fields = ('name', 'product_type__name')