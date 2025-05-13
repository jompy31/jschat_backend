from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Lead, Comment, WorkExperience, Skill

# Define la clase UserProfileInline
class UserProfileInline(admin.StackedInline):
    model = UserProfile

# Define la clase CustomUserAdmin que hereda de UserAdmin
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)

class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0

class LeadAdmin(admin.ModelAdmin):
    inlines = [CommentInline]
    list_display = ['id', 'name', 'email', 'priority', 'status']

# Desregistra el administrador predeterminado de User y registra CustomUserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Lead, LeadAdmin)
admin.site.register(WorkExperience)
admin.site.register(Skill)