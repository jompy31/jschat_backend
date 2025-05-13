from django.contrib import admin
from .models import File, NewsPost, Distributor , Design

class FileAdmin(admin.ModelAdmin):
    list_display = ('id', 'file', 'user', 'created_at')  # Campos a mostrar en la lista de objetos
    list_filter = ('user', 'created_at')  # Campos para filtrar los objetos
    search_fields = ('file', 'user__username')  # Campos para búsqueda
    date_hierarchy = 'created_at'  # Jerarquía de fechas para navegación rápida

class NewsPostAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'datetime')  # Campos a mostrar en la lista de objetos
    list_filter = ('category', 'datetime')  # Campos para filtrar los objetos
    search_fields = ('title', 'description')  # Campos para búsqueda
    date_hierarchy = 'datetime'  # Jerarquía de fechas para navegación rápida

class DistributorAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'country', 'contact_name')  # Campos a mostrar en la lista de objetos
    list_filter = ('country',)  # Campos para filtrar los objetos
    search_fields = ('name', 'contact_name')  # Campos para búsqueda

class DesignAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_by', 'created_at', 'url')  # Campos a mostrar en la lista de objetos
    list_filter = ('created_by', 'created_at')  # Campos para filtrar los objetos
    search_fields = ('name', 'created_by__username')  # Campos para búsqueda
    date_hierarchy = 'created_at'  # Jerarquía de fechas para navegación rápida

admin.site.register(File, FileAdmin)
admin.site.register(NewsPost, NewsPostAdmin)
admin.site.register(Distributor, DistributorAdmin)
admin.site.register(Design, DesignAdmin) 