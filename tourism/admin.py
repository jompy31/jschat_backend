from django.contrib import admin
from .models import Property, PropertyImage, Booking, Payment, Review, Amenity

# Configuración del modelo PropertyImage
class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1  # Número de formularios en blanco para añadir nuevas imágenes

# Configuración del modelo Amenity
@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Configuración del modelo Property
@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'location', 'price_per_night', 'availability')
    list_filter = ('property_type', 'availability', 'owner')
    search_fields = ('title', 'description', 'location')
    inlines = [PropertyImageInline]

    # Personaliza el formulario para incluir la creación de nuevas amenidades
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Aquí puedes hacer algo adicional si necesitas personalizar el formulario
        return form

    def save_model(self, request, obj, form, change):
        # Guardar la propiedad antes de asignar amenidades
        super().save_model(request, obj, form, change)

# Configuración del modelo Booking
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('guest', 'property', 'check_in', 'check_out', 'total_price', 'status')
    list_filter = ('status', 'property', 'guest')
    search_fields = ('guest__username', 'property__title')

# Configuración del modelo Payment
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'booking', 'amount', 'payment_method', 'payment_status')
    list_filter = ('payment_method', 'payment_status', 'booking__property')
    search_fields = ('user__username', 'booking__property__title')

# Configuración del modelo Review
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'property', 'rating', 'comment')
    list_filter = ('property', 'rating')
    search_fields = ('user__username', 'property__title', 'comment')

# Registro de los modelos en el panel de administración
admin.site.register(PropertyImage)  # No se necesita un ModelAdmin personalizado si solo se utilizan inlines.
