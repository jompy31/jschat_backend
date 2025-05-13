from django.contrib import admin
from .models import Property, Review

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'location', 'country', 'province', 'canton', 'rating')
    search_fields = ('title', 'owner__username', 'location', 'country', 'province', 'canton')
    list_filter = ('country', 'province', 'canton', 'rating')
    ordering = ('title',)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('property', 'user', 'rating', 'createdAt')
    search_fields = ('property__title', 'user__username')
    list_filter = ('rating', 'createdAt')
    ordering = ('-createdAt',)
