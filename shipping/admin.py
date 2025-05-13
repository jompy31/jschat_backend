from django.contrib import admin
from .models import (
    Product, 
    Review, 
    Order, 
    OrderItem, 
    ShippingAddress, 
    ProductImage,
    Form,
    FormField,
    FormResponse
)

class OrderItemInline(admin.TabularInline):  # You can use StackedInline if you prefer a different layout
    model = OrderItem
    extra = 1  # Number of empty forms to show

class ShippingAddressInline(admin.TabularInline):
    model = ShippingAddress
    extra = 1  # Number of empty forms to show

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'subproduct', 'category', 'subcategory', 'price', 'countInStock']
    search_fields = ['name', 'category', 'subcategory']  # Agregar búsqueda
    list_filter = ['category', 'price']  # Filtros para la vista de lista

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'comment', 'createdAt']
    search_fields = ['product__name', 'user__username']  # Búsqueda por nombre del producto y usuario

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'comment']
    search_fields = ['product__name']  # Búsqueda por nombre del producto

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['user', 'paymentMethod', 'totalPrice', 'isPaid', 'isDeliver', 'createdAt']
    list_filter = ['isPaid', 'isDeliver']  # Filtros para la vista de lista

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['product', 'order', 'name', 'qty', 'price']
    search_fields = ['product__name', 'order__user__username']  # Búsqueda por producto y usuario de la orden

@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ['order', 'address', 'city', 'postalCode', 'country', 'shippingPrice']

@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'created_at']
    search_fields = ['name', 'user__username']  # Búsqueda por nombre del formulario y usuario

@admin.register(FormField)
class FormFieldAdmin(admin.ModelAdmin):
    list_display = ['form', 'label', 'field_type', 'required']
    search_fields = ['label', 'form__name']  # Búsqueda por etiqueta del campo y nombre del formulario

@admin.register(FormResponse)
class FormResponseAdmin(admin.ModelAdmin):
    list_display = ['form', 'product', 'user', 'form_field']
    search_fields = ['form__name', 'product__name', 'user__username']  # Búsqueda por formulario, producto y usuario


