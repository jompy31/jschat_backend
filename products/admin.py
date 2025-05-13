from django.contrib import admin
from .models import Product, Characteristic, SubProduct, Service, Combo, BusinessHour, TeamMember, Coupon

class CharacteristicInline(admin.TabularInline):
    model = Product.characteristics.through  # Many-to-many through model
    extra = 1
    verbose_name_plural = "Characteristics"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "characteristic":
            kwargs["queryset"] = Characteristic.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'characteristic':
            formfield.label_from_instance = lambda obj: f'{obj.name} - {obj.description}'
        return formfield

class BusinessHourInline(admin.TabularInline):
    model = SubProduct.business_hours.through  # Many-to-many through model
    extra = 1
    verbose_name_plural = "Business Hours"

class TeamMemberInline(admin.TabularInline):
    model = SubProduct.team_members.through  # Many-to-many through model
    extra = 1
    verbose_name_plural = "Team Members"

class CouponInline(admin.TabularInline):
    model = SubProduct.coupons.through  # Many-to-many through model
    extra = 1
    verbose_name_plural = "Coupons"

@admin.register(SubProduct)
class SubProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'phone', 'email', 'address', 'url', 'product_names', 'addressmap', 'constitucion', 'certified')
    search_fields = ('name', 'product_names', 'email', 'address')
    list_filter = ('certified', 'country', 'province', 'canton', 'distrito')
    inlines = [BusinessHourInline, TeamMemberInline, CouponInline]
    fieldsets = (
        ('General Information', {
            'fields': ('name', 'phone', 'email', 'address', 'addressmap', 'image', 'url', 'products', 'subcategory', 'subsubcategory', 'product_names', 'description')
        }),
        ('Location Details', {
            'fields': ('country', 'province', 'canton', 'distrito')
        }),
        ('Other Details', {
            'fields': ('constitucion', 'contact_name', 'phone_number', 'comercial_activity', 'pay_method', 'logo', 'file', 'certified')
        }),
    )

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'created_at')
    list_filter = ('user', 'created_at')
    search_fields = ('name', 'user__username')
    date_hierarchy = 'created_at'
    inlines = [CharacteristicInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('characteristics', 'subproducts')

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'price', 'get_subproduct_name')
    search_fields = ('name', 'description', 'subproduct__name')

    def get_subproduct_name(self, obj):
        return obj.subproduct.name if obj.subproduct else None

    get_subproduct_name.short_description = 'Subproduct Name'

@admin.register(Combo)
class ComboAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'price')
    filter_horizontal = ('services',)

@admin.register(BusinessHour)
class BusinessHourAdmin(admin.ModelAdmin):
    list_display = ('id', 'day', 'start_time', 'end_time')
    list_filter = ('day',)

@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('id', 'description', 'image')
    search_fields = ('description',)
