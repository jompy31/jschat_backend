# backend\api\models.py
from django.db import models, transaction
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import uuid
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Debug signal to log post_save triggers
@receiver(post_save, sender='api.Order')
def debug_post_save(sender, instance, created, **kwargs):
    logger.debug(f"post_save signal triggered for Order {instance.order_number}, created={created}, status={instance.status}, pedido_number={instance.pedido_number}")

# Signal to manage ProductionQueue
@receiver(post_save, sender='api.Order')
def manage_production_queue(sender, instance, created, **kwargs):
    if instance.delivery_date and instance.status in ['in_progress', 'design_pending', 'design_confirmed']:
        queue_type = instance.order_type
        ProductionQueue.objects.update_or_create(
            order=instance,
            defaults={
                'queue_type': queue_type,
                'delivery_date': instance.delivery_date,
                'created_at': instance.created_at
            }
        )
        logger.debug(f"ProductionQueue updated/created for Order {instance.order_number}")

# Signal to update Order dates based on OrderEvent
@receiver(post_save, sender='api.OrderEvent')
def update_order_dates(sender, instance, created, **kwargs):
    order = instance.order
    if instance.event_type == 'payment_50_confirmed':
        order.payment_50_date = instance.timestamp.date()
    elif instance.event_type == 'design_approved':
        order.design_confirmation_date = instance.timestamp.date()
        order.status = 'design_confirmed'
    elif instance.event_type == 'delivered':
        order.delivery_date = instance.timestamp.date()
        order.status = 'completed'
    order.save()
    logger.debug(f"Order {order.order_number} dates updated based on event {instance.event_type}")

@receiver(post_delete, sender='api.OrderEvent')
def update_order_dates_on_delete(sender, instance, **kwargs):
    order = instance.order
    # Check if there are other events of the same type
    if instance.event_type == 'payment_50_confirmed' and not OrderEvent.objects.filter(order=order, event_type='payment_50_confirmed').exists():
        order.payment_50_date = None
    elif instance.event_type == 'design_approved' and not OrderEvent.objects.filter(order=order, event_type='design_approved').exists():
        order.design_confirmation_date = None
        if order.status == 'design_confirmed':
            order.status = 'in_progress'
    elif instance.event_type == 'delivered' and not OrderEvent.objects.filter(order=order, event_type='delivered').exists():
        order.delivery_date = None
        if order.status == 'completed':
            order.status = 'in_progress'
    order.save()
    logger.debug(f"Order {order.order_number} dates updated after deleting event {instance.event_type}")

# Modelo para perfiles de usuario
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    staff_status = models.CharField(
        max_length=20,
        choices=(
            ('customer', 'Customer'),
            ('administrator', 'Administrator'),
            ('sales', 'Sales'),
            ('design', 'Design'),
        ),
        default='customer'
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    def __str__(self):
        return self.user.username

# Modelo para clientes
class Customer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    id_type = models.CharField(max_length=50, blank=True, null=True)
    id_number = models.CharField(max_length=50, unique=True)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    company = models.CharField(max_length=255, blank=True, null=True)
    tipo_contacto = models.CharField(
        max_length=20,
        choices=(('Cliente', 'Cliente'), ('Proveedor', 'Proveedor')),
        default='Cliente'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_profile')
    
    def __str__(self):
        return self.name

# Modelo para pedidos
class Order(models.Model):
    order_number = models.CharField(max_length=10, unique=True, blank=True)
    pedido_number = models.CharField(max_length=10, unique=True, blank=True, null=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order_date = models.DateField(blank=True, null=True)
    payment_50_date = models.DateField(blank=True, null=True)
    design_confirmation_date = models.DateField(blank=True, null=True)
    delivery_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=(
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('design_pending', 'Design Pending'),
            ('design_confirmed', 'Design Confirmed'),
            ('completed', 'Completed'),
        ),
        default='pending'
    )
    order_type = models.CharField(
        max_length=20,
        choices=(('normal', 'Normal'), ('urgent', 'Urgent')),
        default='normal'
    )
    
    def __str__(self):
        return self.order_number or f"Order {self.id}"
    
    def save(self, *args, **kwargs):
        # Only set order_number during creation
        if not self.order_number and not self.pk:
            with transaction.atomic():
                last_order = Order.objects.select_for_update().order_by('-id').first()
                if last_order and last_order.order_number:
                    last_number = int(last_order.order_number[1:])
                    self.order_number = f"O{last_number + 1:08d}"
                else:
                    self.order_number = "O00000001"
        super().save(*args, **kwargs)
    
    def assign_pedido_number(self):
        # Only assign pedido_number if status is 'in_progress' and other conditions are met
        if not self.pedido_number and self.status == 'in_progress' and self.delivery_date and self.payment_50_date and self.design_confirmation_date:
            with transaction.atomic():
                prefix = 'PU' if self.order_type == 'urgent' else 'P'
                existing_numbers = Order.objects.select_for_update().filter(
                    order_type=self.order_type,
                    pedido_number__startswith=prefix
                ).exclude(id=self.id).values_list('pedido_number', flat=True)
                
                max_number = 0
                for num in existing_numbers:
                    if num:  # Skip null values
                        try:
                            num_value = int(num[len(prefix):])
                            max_number = max(max_number, num_value)
                        except (ValueError, TypeError):
                            continue
                
                new_number = max_number + 1
                proposed_pedido_number = f"{prefix}{new_number:08d}"
                
                # Ensure uniqueness
                counter = 1
                while Order.objects.filter(pedido_number=proposed_pedido_number).exists():
                    new_number = max_number + counter
                    proposed_pedido_number = f"{prefix}{new_number:08d}"
                    counter += 1
                
                self.pedido_number = proposed_pedido_number
                logger.debug(f"Assigned pedido_number {self.pedido_number} to order {self.order_number}")
                super().save(update_fields=['pedido_number'])
        else:
            logger.debug(f"Skipped pedido_number assignment for order {self.order_number}: conditions not met")

# Modelo para ítems de un pedido
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.SET_NULL, null=True, blank=True)
    product_type = models.ForeignKey('products.ProductType', on_delete=models.SET_NULL, null=True, blank=True)
    design_file = models.FileField(upload_to='order_designs/', blank=True, null=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.quantity} x {self.product or self.product_type} in Order {self.order.order_number}"

# Modelo para detalles de uniformes
class UniformDetail(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='uniform_detail')
    shirt_quantity = models.PositiveIntegerField(default=0)
    shirt_fabric = models.CharField(max_length=100, blank=True, null=True)
    pants_quantity = models.PositiveIntegerField(default=0)
    pants_fabric = models.CharField(max_length=100, blank=True, null=True)
    polo_quantity = models.PositiveIntegerField(default=0)
    polo_fabric = models.CharField(max_length=100, blank=True, null=True)
    bag_quantity = models.PositiveIntegerField(default=0)
    bag_fabric = models.CharField(max_length=100, blank=True, null=True)
    player_uniform_photo = models.ImageField(upload_to='uniform_photos/', blank=True, null=True)
    goalkeeper_uniform_photo = models.ImageField(upload_to='uniform_photos/', blank=True, null=True)
    neck_photo = models.ImageField(upload_to='uniform_photos/', blank=True, null=True)
    pants_photo = models.ImageField(upload_to='uniform_photos/', blank=True, null=True)
    sponsorships = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Uniform Detail for Order {self.order.order_number}"

# Modelo para lista de jugadores
class Player(models.Model):
    uniform_detail = models.ForeignKey(UniformDetail, on_delete=models.CASCADE, related_name='players')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    number = models.PositiveIntegerField()
    size = models.CharField(max_length=10)
    gender = models.CharField(max_length=1, choices=(('H', 'Hombre'), ('M', 'Mujer')))
    observaciones = models.TextField(blank=True, null=True)
    variaciones = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.number}"

# Modelo para eventos de pedidos
class OrderEvent(models.Model):
    EVENT_TYPES = [
        ('design_approved', 'Design Approved'),
        ('payment_50_confirmed', '50% Payment Confirmed'),
        ('delivered', 'Delivered'),
    ]
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    document = models.FileField(upload_to='order_events/', blank=True, null=True)
    
    def __str__(self):
        return f"{self.get_event_type_display()} for Order {self.order.order_number} by {self.user}"

# Modelo para promociones
class Promotion(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    min_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount = models.DecimalField(max_digits=5, decimal_places=2)
    products = models.ManyToManyField('products.Product', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    def __str__(self):
        return self.name
    
# Modelo para puntos de clientes
class CustomerPoints(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    points = models.PositiveIntegerField(default=0)
    earned_at = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(Tag, blank=True)
    def __str__(self):
        return f"{self.points} points for {self.customer.name}"

# Modelo para colas de producción
class ProductionQueue(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    queue_type = models.CharField(
        max_length=10, 
        choices=(('normal', 'Normal'), ('urgent', 'Urgent'))
    )
    delivery_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.queue_type} Queue for Order {self.order.order_number}"
    
# Modelo para facturas
class Invoice(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(max_length=10, unique=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    issued_date = models.DateField(auto_now_add=True)
    signature_field = models.CharField(max_length=255, blank=True, null=True)
    reviewed_date = models.DateField(blank=True, null=True)
    packed_date = models.DateField(blank=True, null=True)
    delivered_date = models.DateField(blank=True, null=True)
    is_urgent = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Invoice {self.invoice_number} for Order {self.order.order_number}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            with transaction.atomic():
                last_invoice = Invoice.objects.select_for_update().order_by('-id').first()
                if last_invoice and last_invoice.invoice_number:
                    last_number = int(last_invoice.invoice_number[1:])
                    self.invoice_number = f"I{last_number + 1:08d}"
                else:
                    self.invoice_number = "I00000001"
        self.is_urgent = self.order.order_type == 'urgent'
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['order']),
        ]

# Modelo para pagos
class Payment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(auto_now_add=True)
    payment_type = models.CharField(
        max_length=20,
        choices=(('partial', 'Partial'), ('full', 'Full')),
        default='partial'
    )
    reference_document = models.FileField(upload_to='payment_references/', blank=True, null=True)
    
    def __str__(self):
        return f"Payment of {self.amount} for Order {self.order.order_number}"

    class Meta:
        indexes = [
            models.Index(fields=['order', 'payment_date']),
        ]