from django.contrib import admin
from django.contrib import messages
from django.db.models import Sum
from .models import UserProfile, Customer, Order, OrderItem, UniformDetail, Player, OrderEvent, Promotion, CustomerPoints, ProductionQueue
from products.models import ProductType
from datetime import datetime, timedelta
import logging

# Configure logging
logger = logging.getLogger(__name__)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'staff_status', 'phone_number', 'address')
    list_filter = ('staff_status',)
    search_fields = ('user__username', 'user__email')

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'id_number', 'email', 'phone_number', 'tipo_contacto')
    list_filter = ('tipo_contacto',)
    search_fields = ('name', 'id_number', 'email')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'pedido_number', 'customer', 'order_type', 'status', 'delivery_date')
    list_filter = ('order_type', 'status')
    search_fields = ('order_number', 'pedido_number', 'customer__name')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'product_type', 'quantity', 'unit_price')
    search_fields = ('order__order_number',)

@admin.register(UniformDetail)
class UniformDetailAdmin(admin.ModelAdmin):
    list_display = ('order', 'shirt_quantity', 'pants_quantity', 'polo_quantity', 'bag_quantity')
    search_fields = ('order__order_number',)

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('uniform_detail', 'first_name', 'last_name', 'number', 'size', 'gender')
    search_fields = ('first_name', 'last_name', 'uniform_detail__order__order_number')

@admin.register(OrderEvent)
class OrderEventAdmin(admin.ModelAdmin):
    list_display = ('order', 'event_type', 'user', 'timestamp')
    list_filter = ('event_type',)
    search_fields = ('order__order_number', 'user__username')

@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_amount', 'discount', 'created_at')
    search_fields = ('name',)

@admin.register(CustomerPoints)
class CustomerPointsAdmin(admin.ModelAdmin):
    list_display = ('customer', 'points', 'earned_at')
    search_fields = ('customer__name',)

@admin.register(ProductionQueue)
class ProductionQueueAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer_name', 'queue_type', 'delivery_date', 'total_quantity', 'order_status')
    list_filter = ('queue_type', 'order__status', 'delivery_date')
    search_fields = ('order__order_number', 'order__customer__name')
    actions = ['reassign_delivery_dates']

    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = 'Order Number'

    def customer_name(self, obj):
        return obj.order.customer.name
    customer_name.short_description = 'Customer'

    def total_quantity(self, obj):
        return obj.order.items.aggregate(total=Sum('quantity'))['total'] or 0
    total_quantity.short_description = 'Total Quantity'

    def order_status(self, obj):
        return obj.order.get_status_display()
    order_status.short_description = 'Order Status'

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return ['order', 'queue_type']
        return []

    def save_model(self, request, obj, form, change):
        """Validate production queue capacity and delivery date before saving."""
        logger.debug(f"Saving ProductionQueue for order {obj.order.order_number}, delivery_date: {obj.delivery_date}")
        product_type_quantities = {}
        
        # Calculate total quantities per product type for the order
        for item in obj.order.items.all():
            product_type = item.product_type or (item.product.product_type if item.product else None)
            if product_type:
                product_type_id = product_type.id
                product_type_quantities[product_type_id] = product_type_quantities.get(product_type_id, 0) + item.quantity

        # Check production capacity for the delivery date
        for product_type_id, requested_quantity in product_type_quantities.items():
            product_type = ProductType.objects.get(id=product_type_id)
            existing_queues = ProductionQueue.objects.filter(
                delivery_date=obj.delivery_date,
                order__items__product_type=product_type
            ).exclude(order=obj.order).distinct()
            existing_quantity = sum(
                item.quantity for queue in existing_queues
                for item in queue.order.items.filter(product_type=product_type)
            )
            total_quantity = existing_quantity + requested_quantity

            if total_quantity > product_type.daily_production_capacity:
                messages.error(
                    request,
                    f"Cannot save: Total quantity ({total_quantity}) for {product_type.name} on {obj.delivery_date} "
                    f"exceeds daily production capacity ({product_type.daily_production_capacity})."
                )
                return

        # Validate delivery date against delivery_time_days
        base_date = obj.order.payment_50_date or obj.order.created_at.date()
        max_delivery_days = max(
            (item.product_type or item.product.product_type).delivery_time_days
            for item in obj.order.items.all()
        )
        min_delivery_date = base_date + timedelta(days=max_delivery_days)
        if obj.delivery_date < min_delivery_date:
            messages.warning(
                request,
                f"Delivery date {obj.delivery_date} is earlier than the minimum required date ({min_delivery_date}) "
                f"based on product type delivery time ({max_delivery_days} days)."
            )

        obj.queue_type = obj.order.order_type
        super().save_model(request, obj, form, change)
        logger.info(f"ProductionQueue saved for order {obj.order.order_number} with delivery_date {obj.delivery_date}")

    def reassign_delivery_dates(self, request, queryset):
        """Reassign delivery dates for selected queues based on capacity and delivery_time_days."""
        for queue in queryset:
            order = queue.order
            base_date = order.payment_50_date or order.created_at.date()
            product_type_quantities = {}
            max_delivery_days = 0

            # Calculate quantities and max delivery time
            for item in order.items.all():
                product_type = item.product_type or (item.product.product_type if item.product else None)
                if product_type:
                    product_type_id = product_type.id
                    product_type_quantities[product_type_id] = product_type_quantities.get(product_type_id, 0) + item.quantity
                    max_delivery_days = max(max_delivery_days, product_type.delivery_time_days)

            # Find the earliest available delivery date
            proposed_date = base_date + timedelta(days=max_delivery_days)
            while True:
                capacity_ok = True
                for product_type_id, requested_quantity in product_type_quantities.items():
                    product_type = ProductType.objects.get(id=product_type_id)
                    existing_queues = ProductionQueue.objects.filter(
                        delivery_date=proposed_date,
                        order__items__product_type=product_type
                    ).exclude(order=order).distinct()
                    existing_quantity = sum(
                        item.quantity for queue in existing_queues
                        for item in queue.order.items.filter(product_type=product_type)
                    )
                    total_quantity = existing_quantity + requested_quantity
                    if total_quantity > product_type.daily_production_capacity:
                        capacity_ok = False
                        break
                if capacity_ok:
                    queue.delivery_date = proposed_date
                    queue.save()
                    order.delivery_date = proposed_date
                    order.save()
                    messages.info(
                        request,
                        f"Reassigned delivery date for order {order.order_number} to {proposed_date}."
                    )
                    logger.info(f"Reassigned delivery_date for order {order.order_number} to {proposed_date}")
                    break
                proposed_date += timedelta(days=1)

    reassign_delivery_dates.short_description = "Reassign delivery dates based on capacity"