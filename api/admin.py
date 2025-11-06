# backend_github/jschat_backend/api/admin.py
from django.contrib import admin
from django.db.models import Sum, F, DecimalField, ExpressionWrapper, Value
from django.db.models.functions import Coalesce, Cast
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from datetime import timedelta
import logging

from .models import (
    UserProfile, Customer, Order, OrderItem, UniformDetail,
    Player, OrderEvent, Promotion, CustomerPoints,
    ProductionQueue, Invoice, Payment, PointsConfig, Tag
)
from products.models import ProductType, Product

logger = logging.getLogger(__name__)

# ====================== INLINE CLASSES ======================

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    fields = ('product', 'product_type', 'quantity', 'design_file', 'unit_price_display', 'subtotal')
    readonly_fields = ('unit_price_display', 'subtotal')

    def unit_price_display(self, obj):
        return f"${obj.unit_price:.2f}" if obj.pk and obj.unit_price else "-"
    unit_price_display.short_description = "Precio Unit."

    def subtotal(self, obj):
        if obj.pk and obj.quantity and obj.unit_price:
            return f"${obj.quantity * obj.unit_price:.2f}"
        return "-"
    subtotal.short_description = "Subtotal"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'product_type')


class PlayerInline(admin.TabularInline):
    model = Player
    extra = 1
    fields = ('first_name', 'last_name', 'number', 'size', 'gender', 'observaciones', 'variaciones', 'full_name')
    readonly_fields = ('full_name',)  # Only full_name should be readonly
    can_delete = True  # Ensure deletion is allowed
    can_add = True     # Ensure adding is allowed
    search_fields = ('first_name', 'last_name')
    ordering = ('number',)  # Order players by number for clarity
    verbose_name = "Jugador"
    verbose_name_plural = "Jugadores"

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = "Nombre Completo"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('uniform_detail__order')

    def has_add_permission(self, request, obj=None):
        # Allow adding players if UniformDetail exists
        if obj and hasattr(obj, 'uniform_detail'):
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        # Allow deleting players
        return True


class UniformDetailInline(admin.StackedInline):
    model = UniformDetail
    extra = 0
    fields = (
        'shirt_quantity', 'shirt_fabric', 'shirt_details',
        'pants_quantity', 'pants_fabric', 'pants_details',
        'polo_quantity', 'polo_fabric',
        'bag_quantity', 'bag_fabric',
        'sponsorships',
        'player_uniform_photo', 'goalkeeper_uniform_photo',
        'neck_photo', 'pants_photo', 'total_players'
    )
    readonly_fields = ('shirt_details', 'pants_details', 'total_players')
    inlines = [PlayerInline]
    verbose_name = "Detalles de Uniforme"
    verbose_name_plural = "Detalles de Uniforme"

    def shirt_details(self, obj):
        return f"{obj.shirt_quantity} unidades, Tela: {obj.shirt_fabric or 'N/A'}"
    shirt_details.short_description = "Detalles Camisa"

    def pants_details(self, obj):
        return f"{obj.pants_quantity} unidades, Tela: {obj.pants_fabric or 'N/A'}"
    pants_details.short_description = "Detalles Pantalón"

    def total_players(self, obj):
        return obj.players.count()
    total_players.short_description = "Total Jugadores"

    def has_add_permission(self, request, obj=None):
        # Allow adding UniformDetail only if it doesn't exist yet
        if obj and hasattr(obj, 'uniform_detail'):
            return False
        return True


class OrderEventInline(admin.TabularInline):
    model = OrderEvent
    extra = 1
    fields = ('event_type', 'user', 'timestamp', 'amount', 'document', 'linked_payment')
    readonly_fields = ('timestamp', 'linked_payment')

    def linked_payment(self, obj):
        if obj.pk and obj.event_type == 'payment':
            payment = Payment.objects.filter(
                order=obj.order,
                amount=obj.amount,
                payment_date=obj.timestamp.date()
            ).first()
            if payment:
                url = reverse("admin:api_payment_change", args=[payment.id])
                return format_html('<a href="{}">Ver Pago</a>', url)
        return "-"
    linked_payment.short_description = "Pago"


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 1
    fields = ('amount', 'payment_date', 'payment_type', 'reference_document')
    readonly_fields = ('payment_date',)


# ====================== ADMIN CLASSES ======================

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'staff_status', 'phone_number', 'profile_picture_tag')
    list_filter = ('staff_status',)
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('profile_picture_tag',)

    def profile_picture_tag(self, obj):
        if obj.profile_picture:
            return format_html('<img src="{}" width="50" height="50" style="border-radius:50%;"/>', obj.profile_picture.url)
        return "-"
    profile_picture_tag.short_description = "Foto"


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'id_number', 'email', 'phone_number', 'tipo_contacto', 'total_orders', 'total_spent')
    list_filter = ('tipo_contacto', 'created_at')
    search_fields = ('name', 'id_number', 'email', 'phone_number')
    readonly_fields = ('total_orders', 'total_spent')

    def total_orders(self, obj):
        return obj.orders.count()
    total_orders.short_description = "Pedidos"

    def total_spent(self, obj):
        total = obj.orders.filter(status='completed').aggregate(
            total=Coalesce(
                Sum(
                    ExpressionWrapper(
                        Cast('items__quantity', output_field=DecimalField(max_digits=12, decimal_places=2)) *
                        F('items__unit_price'),
                        output_field=DecimalField(max_digits=12, decimal_places=2)
                    )
                ), 
                Value(0.0),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        )['total'] or 0
        return f"${total:.2f}"
    total_spent.short_description = "Total Gastado"

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'pedido_number', 'customer_link', 'order_type',
        'status', 'total_amount', 'paid_amount', 'payment_percentage',
        'delivery_date', 'created_by', 'invoice_link', 'uniform_summary'
    )
    list_filter = (
        'status', 'order_type', 'delivery_date', 'created_at',
        'customer__tipo_contacto'
    )
    search_fields = (
        'order_number', 'pedido_number', 'customer__name',
        'customer__id_number', 'created_by__username'
    )
    readonly_fields = (
        'order_number', 'pedido_number', 'created_by', 'created_at',
        'updated_at', 'payment_percentage', 'total_amount', 'paid_amount',
        'uniform_summary', 'players_summary'
    )
    inlines = [OrderItemInline, UniformDetailInline, OrderEventInline, PaymentInline]
    fieldsets = (
        ('Información General', {
            'fields': ('order_number', 'pedido_number', 'customer', 'created_by', 'order_type', 'status')
        }),
        ('Fechas', {
            'fields': ('order_date', 'delivery_date', 'created_at', 'updated_at')
        }),
        ('Financiero', {
            'fields': ('total_amount', 'paid_amount', 'payment_percentage')
        }),
        ('Resumen de Uniformes y Jugadores', {
            'fields': ('uniform_summary', 'players_summary'),
            'classes': ('collapse',)
        }),
    )
    actions = ['mark_as_in_progress', 'mark_as_completed', 'generate_invoices']

    def uniform_summary(self, obj):
        if hasattr(obj, 'uniform_detail'):
            ud = obj.uniform_detail
            summary = (
                f"Camisas: {ud.shirt_quantity} ({ud.shirt_fabric or 'N/A'}), "
                f"Pantalones: {ud.pants_quantity} ({ud.pants_fabric or 'N/A'}), "
                f"Polos: {ud.polo_quantity} ({ud.polo_fabric or 'N/A'}), "
                f"Bolsas: {ud.bag_quantity} ({ud.bag_fabric or 'N/A'})"
            )
            if ud.sponsorships:
                summary += f", Patrocinios: {ud.sponsorships}"
            return summary
        return "Sin detalles de uniforme"
    uniform_summary.short_description = "Resumen Uniformes"

    def players_summary(self, obj):
        if hasattr(obj, 'uniform_detail'):
            players = obj.uniform_detail.players.all()
            if players:
                return format_html(
                    "<br>".join(
                        f"Nº {p.number}: {p.first_name} {p.last_name}, Talla: {p.size}, "
                        f"Género: {p.get_gender_display()}, "
                        f"Obs: {p.observaciones or 'N/A'}, Var: {p.variaciones or 'N/A'}"
                        for p in players
                    )
                )
            return "Sin jugadores registrados"
        return "Sin jugadores registrados"
    players_summary.short_description = "Resumen Jugadores"

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        if form.save_m2m:
            form.save_m2m()
        should_calculate = False
        if not change:
            if obj.status == 'in_progress' and obj.items.exists():
                should_calculate = True
        else:
            try:
                old = Order.objects.only('status', 'order_type').get(pk=obj.pk)
                if old.status != 'in_progress' and obj.status == 'in_progress' and obj.items.exists():
                    should_calculate = True
            except Order.DoesNotExist:
                pass
        if should_calculate:
            is_personalizado = obj.order_type == 'personalizado'
            if not is_personalizado or not obj.delivery_date:
                if not is_personalizado:
                    obj.delivery_date = None
                obj.calculate_delivery_date()
                if obj.delivery_date:
                    obj.save(update_fields=['delivery_date'])
                    logger.info(f"[ADMIN] Fecha de entrega asignada: {obj.delivery_date} para {obj.order_number}")
        if obj.status == 'in_progress' and obj.delivery_date and not obj.pedido_number:
            obj.assign_pedido_number()

    def customer_link(self, obj):
        url = reverse("admin:api_customer_change", args=[obj.customer.id])
        return format_html('<a href="{}">{}</a>', url, obj.customer.name)
    customer_link.short_description = "Cliente"

    def invoice_link(self, obj):
        if hasattr(obj, 'invoice'):
            url = reverse("admin:api_invoice_change", args=[obj.invoice.id])
            return format_html('<a href="{}">Ver Factura</a>', url)
        return "-"
    invoice_link.short_description = "Factura"

    def mark_as_in_progress(self, request, queryset):
        updated = 0
        for order in queryset:
            if order.status != 'in_progress':
                order.status = 'in_progress'
                order.save()
                updated += 1
        self.message_user(request, f"{updated} pedidos marcados como 'En Progreso'. Fecha de entrega recalculada.")
    mark_as_in_progress.short_description = "Marcar como En Progreso (recalcula fecha)"

    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f"{updated} pedidos marcados como 'Completado'.")
    mark_as_completed.short_description = "Marcar como Completado"

    def generate_invoices(self, request, queryset):
        created = 0
        for order in queryset.filter(invoice__isnull=True, status='completed'):
            Invoice.objects.create(
                order=order,
                total_amount=order.total_amount,
                tax=order.total_amount * 0.13,
            )
            created += 1
        self.message_user(request, f"{created} facturas generadas.")
    generate_invoices.short_description = "Generar Facturas"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_name', 'quantity', 'unit_price', 'subtotal')
    list_filter = ('order__status',)
    search_fields = ('order__order_number',)

    def product_name(self, obj):
        return obj.product.name if obj.product else obj.product_type.name
    product_name.short_description = "Producto"

    def subtotal(self, obj):
        return f"${obj.quantity * obj.unit_price:.2f}"
    subtotal.short_description = "Subtotal"


@admin.register(UniformDetail)
class UniformDetailAdmin(admin.ModelAdmin):
    list_display = ('order', 'shirt_quantity', 'pants_quantity', 'total_players', 'sponsorships_summary')
    search_fields = ('order__order_number',)
    inlines = [PlayerInline]

    def total_players(self, obj):
        return obj.players.count()
    total_players.short_description = "Jugadores"

    def sponsorships_summary(self, obj):
        return obj.sponsorships if obj.sponsorships else "Sin patrocinios"
    sponsorships_summary.short_description = "Patrocinios"


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('uniform_detail', 'full_name', 'number', 'size', 'gender', 'observaciones', 'variaciones')
    search_fields = ('first_name', 'last_name', 'uniform_detail__order__order_number')

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = "Nombre"


@admin.register(OrderEvent)
class OrderEventAdmin(admin.ModelAdmin):
    list_display = ('order', 'event_type', 'user', 'amount', 'timestamp', 'document_link')
    list_filter = ('event_type', 'timestamp')
    search_fields = ('order__order_number', 'user__username')
    readonly_fields = ('timestamp',)

    def document_link(self, obj):
        if obj.document:
            return format_html('<a href="{}">Ver documento</a>', obj.document.url)
        return "-"
    document_link.short_description = "Documento"


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ('name', 'discount', 'min_amount', 'product_count')
    filter_horizontal = ('products',)

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = "Productos"


@admin.register(CustomerPoints)
class CustomerPointsAdmin(admin.ModelAdmin):
    list_display = ('customer', 'points', 'earned_at', 'reason', 'config_link')
    list_filter = ('earned_at',)
    search_fields = ('customer__name', 'reason')
    filter_horizontal = ('tags',)  # Para administrar tags fácilmente
    readonly_fields = ('earned_at', 'config_link')

    def config_link(self, obj):
        if obj.config:
            url = reverse("admin:api_pointsconfig_change", args=[obj.config.id])
            return format_html('<a href="{}">{}</a>', url, obj.config.name)
        return "-"
    config_link.short_description = "Configuración"


@admin.register(ProductionQueue)
class ProductionQueueAdmin(admin.ModelAdmin):
    list_display = (
        'order_link', 'customer_name', 'queue_type',
        'delivery_date', 'total_quantity', 'status', 'capacity_status'
    )
    list_filter = ('queue_type', 'delivery_date', 'order__status')
    search_fields = ('order__order_number', 'order__customer__name')
    readonly_fields = ('order', 'queue_type', 'created_at')
    actions = ['reassign_delivery_dates']

    def order_link(self, obj):
        url = reverse("admin:api_order_change", args=[obj.order.id])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
    order_link.short_description = "Pedido"

    def customer_name(self, obj):
        return obj.order.customer.name
    customer_name.short_description = "Cliente"

    def total_quantity(self, obj):
        return obj.order.items.aggregate(total=Sum('quantity'))['total'] or 0
    total_quantity.short_description = "Cant."

    def status(self, obj):
        return obj.order.get_status_display()
    status.short_description = "Estado"

    def capacity_status(self, obj):
        over = False
        for item in obj.order.items.all():
            pt = item.product_type or (item.product.product_type if item.product else None)
            if pt:
                existing = ProductionQueue.objects.filter(
                    delivery_date=obj.delivery_date
                ).exclude(order=obj.order)
                total = sum(
                    i.quantity for q in existing
                    for i in q.order.items.filter(
                        product_type=pt
                    )
                ) + item.quantity
                if total > pt.daily_production_capacity:
                    over = True
        return "Excede" if over else "OK"
    capacity_status.short_description = "Capacidad"

    def reassign_delivery_dates(self, request, queryset):
        reassigned = 0
        for queue in queryset:
            order = queue.order
            base_date = order.payment_50_date or order.created_at.date()
            max_days = max(
                (i.product_type or i.product.product_type).delivery_time_days
                for i in order.items.all()
            )
            proposed = base_date + timedelta(days=max_days)
            while True:
                ok = True
                for item in order.items.all():
                    pt = item.product_type or (item.product.product_type if item.product else None)
                    if pt:
                        existing = ProductionQueue.objects.filter(delivery_date=proposed).exclude(order=order)
                        total = sum(i.quantity for q in existing for i in q.order.items.filter(product_type=pt)) + item.quantity
                        if total > pt.daily_production_capacity:
                            ok = False
                            break
                if ok:
                    queue.delivery_date = proposed
                    queue.save()
                    order.delivery_date = proposed
                    order.save()
                    reassigned += 1
                    break
                proposed += timedelta(days=1)
        self.message_user(request, f"{reassigned} colas reasignadas.")
    reassign_delivery_dates.short_description = "Reasignar fechas por capacidad"


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'order_link', 'total_amount', 'tax', 'issued_date', 'is_urgent')
    list_filter = ('is_urgent', 'issued_date')
    search_fields = ('invoice_number', 'order__order_number')
    readonly_fields = ('invoice_number', 'order', 'issued_date', 'is_urgent')

    def order_link(self, obj):
        url = reverse("admin:api_order_change", args=[obj.order.id])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
    order_link.short_description = "Pedido"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'amount', 'payment_date', 'payment_type', 'document_link')
    list_filter = ('payment_type', 'payment_date')
    search_fields = ('order__order_number',)

    def document_link(self, obj):
        if obj.reference_document:
            return format_html('<a href="{}">Ver</a>', obj.reference_document.url)
        return "-"
    document_link.short_description = "Comprobante"


@admin.register(PointsConfig)
class PointsConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'points_per_amount', 'amount_threshold', 'multiplier', 'is_active', 'is_default', 'start_date', 'end_date')
    list_filter = ('is_active', 'is_default')
    search_fields = ('name',)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)