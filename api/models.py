from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db.models import Sum, Q
from datetime import date, timedelta
import uuid
import logging

# === IMPORTAR PRODUCTOS ===
from products.models import Product, ProductType

logger = logging.getLogger(__name__)

# ====================== USER & CUSTOMER ======================

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


# ====================== ORDER & ITEMS ======================

ORDER_TYPE_CHOICES = [
    ('normal', 'Normal'),
    ('urgent', 'Urgente'),
    ('express', 'Express'),
    ('personalizado', 'Personalizado'),
]
ORDER_TYPE_PRIORITY = {
    'express': 1,
    'urgent': 2,
    'normal': 3,
    'personalizado': 4,
}

EVENT_TYPE_CHOICES = [
    ('payment', 'Pago / Abono'),
    ('payment_50_confirmed', '50% Pago Recibido'),
    ('payment_100_confirmed', '100% Pago Recibido'),
    ('design_approved', 'Diseño Aprobado'),
    ('delivered', 'Entregado'),
]

class Order(models.Model):
    order_number = models.CharField(max_length=10, unique=True, blank=True)
    pedido_number = models.CharField(max_length=12, unique=True, blank=True, null=True)
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='orders')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order_date = models.DateField(blank=True, null=True)
    delivery_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=(
            ('pending', 'Pendiente'),
            ('in_progress', 'En Progreso'),
            ('design_pending', 'Diseño Pendiente'),
            ('design_confirmed', 'Diseño Confirmado'),
            ('completed', 'Completado'),
        ),
        default='pending'
    )
    order_type = models.CharField(
        max_length=20,
        choices=ORDER_TYPE_CHOICES,
        default='normal'
    )

    def __str__(self):
        return self.order_number or f"Order {self.id}"

    @property
    def total_amount(self):
        total = self.items.aggregate(
            total=Sum(
                models.F('quantity') * models.F('unit_price'),
                output_field=models.DecimalField(max_digits=12, decimal_places=2)
            )
        )['total'] or 0
        return round(total, 2)

    @property
    def paid_amount(self):
        total = self.payments.aggregate(total=Sum('amount'))['total'] or 0
        return round(total, 2)

    @property
    def payment_percentage(self):
        if self.total_amount <= 0:
            return 0
        return round((self.paid_amount / self.total_amount) * 100, 2)

    def save(self, *args, **kwargs):
        # === GENERAR order_number SI ES NUEVO ===
        if not self.pk and not self.order_number:
            last = Order.objects.order_by('-id').first()
            num = int(last.order_number[1:]) + 1 if last and last.order_number else 1
            self.order_number = f"O{num:08d}"
        super().save(*args, **kwargs)

    # === CÁLCULO DE FECHA DE ENTREGA ===
    def calculate_delivery_date(self):
        if not self.pk or not self.items.exists():
            self.delivery_date = None
            return

        base_date = self.order_date or date.today()
        items_by_type = {}
        for item in self.items.all():
            pt = item.product.product_type if item.product else item.product_type
            if not pt:
                continue
            items_by_type[pt.id] = items_by_type.get(pt.id, 0) + item.quantity

        if not items_by_type:
            self.delivery_date = None
            return

        product_types = ProductType.objects.filter(id__in=items_by_type.keys())
        pt_data = {pt.id: pt for pt in product_types}

        max_days = 0
        for pt_id, qty in items_by_type.items():
            pt = pt_data.get(pt_id)
            if not pt:
                continue
            base_days = pt.delivery_time_days
            extra_days = max(0, (qty - 1) // pt.daily_production_capacity)
            total_days = base_days + extra_days
            max_days = max(max_days, total_days)

        tentative_date = base_date + timedelta(days=max_days)
        current_date = tentative_date
        priority = ORDER_TYPE_PRIORITY.get(self.order_type, 4)

        while True:
            conflicting = Order.objects.filter(
                delivery_date=current_date,
                status__in=['in_progress', 'design_pending', 'design_confirmed']
            ).exclude(id=self.id)

            higher_priority = conflicting.filter(
                Q(order_type__in=[k for k, v in ORDER_TYPE_PRIORITY.items() if v <= priority])
            )

            load = {}
            for order in higher_priority:
                for item in order.items.all():
                    pt = item.product.product_type if item.product else item.product_type
                    if not pt:
                        continue
                    load[pt.id] = load.get(pt.id, 0) + item.quantity

            can_fit = True
            for pt_id, qty in items_by_type.items():
                pt = pt_data.get(pt_id)
                if not pt:
                    continue
                current_load = load.get(pt_id, 0)
                if current_load + qty > pt.daily_production_capacity:
                    can_fit = False
                    break

            if can_fit:
                self.delivery_date = current_date
                logger.info(f"Fecha de entrega calculada: {current_date} para {self.order_number}")
                return

            current_date += timedelta(days=1)

    # === ASIGNAR pedido_number ===
    def assign_pedido_number(self):
        if self.pedido_number or not self.delivery_date:
            return

        prefix = {
            'normal': 'P',
            'urgent': 'PU',
            'express': 'PE',
            'personalizado': 'PC',
        }.get(self.order_type, 'P')

        existing = Order.objects.filter(
            order_type=self.order_type,
            pedido_number__startswith=prefix
        ).exclude(id=self.id).values_list('pedido_number', flat=True)

        max_num = 0
        for num in existing:
            if num and num.startswith(prefix):
                try:
                    max_num = max(max_num, int(num[len(prefix):]))
                except:
                    continue
        new_num = max_num + 1
        proposed = f"{prefix}{new_num:08d}"

        while Order.objects.filter(pedido_number=proposed).exists():
            new_num += 1
            proposed = f"{prefix}{new_num:08d}"

        self.pedido_number = proposed
        Order.objects.filter(pk=self.pk).update(pedido_number=self.pedido_number)
        logger.info(f"Asignado {self.pedido_number} a {self.order_number}")


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    product_type = models.ForeignKey(ProductType, on_delete=models.SET_NULL, null=True, blank=True)
    design_file = models.FileField(upload_to='order_designs/', blank=True, null=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)

    def __str__(self):
        return f"{self.quantity} x {self.product or self.product_type} in Order {self.order.order_number}"

    def save(self, *args, **kwargs):
        if self.product:
            self.unit_price = self.product.product_type.base_price + self.product.additional_price
        elif self.product_type:
            self.unit_price = self.product_type.base_price
        else:
            self.unit_price = 0
        super().save(*args, **kwargs)


# ====================== SEÑALES CRÍTICAS ======================

@receiver(post_save, sender=Order)
def ensure_delivery_date_and_pedido_number(sender, instance, created, **kwargs):
    """
    GARANTIZA:
    - Si está en 'in_progress' y tiene ítems → calcular delivery_date, asignar pedido_number y crear/actualizar ProductionQueue
    - Si es 'personalizado' y tiene fecha manual → respetar solo si usuario es admin
    - Aplica tanto en creación como en actualización
    """
    if not instance.pk:
        return

    should_calculate = False

    # Verificar si la orden está en 'in_progress' y tiene ítems
    if instance.status == 'in_progress' and instance.items.exists():
        should_calculate = True

    # Si es una actualización, verificar si cambió el estado a 'in_progress'
    if not created:
        try:
            old = Order.objects.only('status').get(pk=instance.pk)
            if old.status != 'in_progress' and instance.status == 'in_progress' and instance.items.exists():
                should_calculate = True
        except Order.DoesNotExist:
            pass

    # Si debe calcularse la fecha de entrega
    if should_calculate:
        user = kwargs.get('context', {}).get('request', {}).get('user')
        is_admin = user and hasattr(user, 'userprofile') and user.userprofile.staff_status == 'administrator'
        
        # Si no es admin o no hay fecha manual, recalcular siempre
        if instance.order_type != 'personalizado' or not instance.delivery_date or not is_admin:
            instance.calculate_delivery_date()
            if instance.delivery_date:
                Order.objects.filter(pk=instance.pk).update(delivery_date=instance.delivery_date)
            else:
                # Si no se puede calcular (p.ej., no hay ítems válidos), establecer como None
                Order.objects.filter(pk=instance.pk).update(delivery_date=None)

        # Asignar pedido_number si no existe y hay delivery_date
        if instance.status == 'in_progress' and instance.delivery_date and not instance.pedido_number:
            instance.assign_pedido_number()

        # Crear o actualizar ProductionQueue si hay delivery_date
        if instance.status == 'in_progress' and instance.delivery_date:
            ProductionQueue.objects.update_or_create(
                order=instance,
                defaults={
                    'queue_type': instance.order_type,
                    'delivery_date': instance.delivery_date,
                    'created_at': instance.created_at
                }
            )
        elif instance.status == 'in_progress' and not instance.delivery_date:
            # Si no hay fecha de entrega, eliminar de la cola
            ProductionQueue.objects.filter(order=instance).delete()

@receiver(post_save, sender='api.OrderItem')
@receiver(post_delete, sender='api.OrderItem')
def recalculate_on_item_change(sender, instance, **kwargs):
    """
    Recalcular delivery_date, asignar pedido_number y actualizar ProductionQueue si cambian ítems y la orden está en 'in_progress'
    """
    order = instance.order
    user = kwargs.get('context', {}).get('request', {}).get('user')
    is_admin = user and hasattr(user, 'userprofile') and user.userprofile.staff_status == 'administrator'

    if order.status == 'in_progress':
        # Solo respetar fecha manual para 'personalizado' si es administrador
        if order.order_type != 'personalizado' or not order.delivery_date or not is_admin:
            order.delivery_date = None
            order.calculate_delivery_date()
            if order.delivery_date:
                Order.objects.filter(pk=order.pk).update(delivery_date=order.delivery_date)
            else:
                Order.objects.filter(pk=order.pk).update(delivery_date=None)

        # Asignar pedido_number si no existe y hay delivery_date
        if order.delivery_date and not order.pedido_number:
            order.assign_pedido_number()

        # Actualizar ProductionQueue si hay delivery_date
        if order.delivery_date:
            ProductionQueue.objects.update_or_create(
                order=order,
                defaults={
                    'queue_type': order.order_type,
                    'delivery_date': order.delivery_date,
                    'created_at': order.created_at
                }
            )
        else:
            # Si no hay fecha de entrega, eliminar de la cola
            ProductionQueue.objects.filter(order=order).delete()


@receiver(pre_save, sender=Order)
def recalculate_on_type_change(sender, instance, **kwargs):
    """
    Recalcular si cambia order_type y está en 'in_progress'
    """
    if not instance.pk:
        return
    try:
        old = Order.objects.only('status', 'order_type').get(pk=instance.pk)
    except Order.DoesNotExist:
        return

    user = kwargs.get('context', {}).get('request', {}).get('user')
    is_admin = user and hasattr(user, 'userprofile') and user.userprofile.staff_status == 'administrator'

    if (old.status == 'in_progress' and 
        instance.status == 'in_progress' and 
        old.order_type != instance.order_type):
        # Solo respetar fecha manual para 'personalizado' si es administrador
        if instance.order_type != 'personalizado' or not instance.delivery_date or not is_admin:
            instance.delivery_date = None  # Forzar recálculo en post_save


# ====================== RESTO DE MODELOS ======================

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

class OrderEvent(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    document = models.FileField(upload_to='order_events/', blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.get_event_type_display()} - {self.order.order_number}"

    def clean(self):
        if self.event_type != 'payment' and self.amount != 0:
            from django.core.exceptions import ValidationError
            raise ValidationError("El monto solo se permite en eventos de tipo 'payment'.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

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

@receiver(post_save, sender=Order)
def manage_production_queue(sender, instance, created, **kwargs):
    """
    Gestionar la cola de producción: crear/actualizar o eliminar según el estado y delivery_date
    """
    if instance.status in ['in_progress', 'design_pending', 'design_confirmed']:
        if instance.delivery_date:
            ProductionQueue.objects.update_or_create(
                order=instance,
                defaults={
                    'queue_type': instance.order_type,
                    'delivery_date': instance.delivery_date,
                    'created_at': instance.created_at
                }
            )
        else:
            # Si no hay fecha de entrega, eliminar de la cola
            ProductionQueue.objects.filter(order=instance).delete()
    else:
        # Si la orden no está en un estado activo, eliminar de la cola
        ProductionQueue.objects.filter(order=instance).delete()

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

@receiver(post_delete, sender='api.OrderEvent')
def update_order_dates_on_delete(sender, instance, **kwargs):
    order = instance.order
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

@receiver(post_save, sender='api.OrderEvent')
def update_order_on_event(sender, instance, created, **kwargs):
    if instance.event_type == 'design_approved':
        instance.order.status = 'design_confirmed'
        instance.order.save(update_fields=['status'])
    elif instance.event_type == 'delivered':
        instance.order.status = 'completed'
        instance.order.save(update_fields=['status'])

@receiver(post_save, sender=OrderEvent)
def sync_event_to_payment(sender, instance, created, **kwargs):
    if instance.event_type != 'payment':
        return
    order = instance.order
    amount = instance.amount or 0
    document = instance.document
    payment_date = instance.timestamp.date()

    payment = Payment.objects.filter(
        order=order,
        amount=amount,
        payment_date=payment_date
    ).first()

    if payment:
        if document:
            payment.reference_document = document
        payment.save()
    else:
        Payment.objects.create(
            order=order,
            amount=amount,
            payment_date=payment_date,
            payment_type='partial' if amount < order.total_amount else 'full',
            reference_document=document
        )

@receiver(post_delete, sender=OrderEvent)
def remove_payment_on_event_delete(sender, instance, **kwargs):
    if instance.event_type != 'payment':
        return
    Payment.objects.filter(
        order=instance.order,
        amount=instance.amount,
        payment_date=instance.timestamp.date()
    ).delete()

# === MODELOS RESTANTES ===
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

class PointsConfig(models.Model):
    name = models.CharField(max_length=100)  # Ej: "Tasa Normal" o "Promo Día de la Madre"
    points_per_amount = models.PositiveIntegerField(default=10)  # Puntos por cada X colones
    amount_threshold = models.DecimalField(max_digits=12, decimal_places=2, default=10000)  # Cada X colones
    multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)  # Multiplicador para promos (ej: 2.0 para doble puntos)
    start_date = models.DateField(blank=True, null=True)  # Para promos temporales
    end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False, help_text="Configuración predeterminada para todas las órdenes")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['is_default'],
                condition=models.Q(is_default=True),
                name='unique_default_points_config'
            )
        ]

    def __str__(self):
        return self.name
    
@receiver(pre_save, sender=PointsConfig)
def ensure_single_default(sender, instance, **kwargs):
    if instance.is_default:
        PointsConfig.objects.filter(is_default=True).exclude(pk=instance.pk).update(is_default=False)

class CustomerPoints(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    points = models.IntegerField(default=0)  # Ahora permite negativos para restas
    earned_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=255, blank=True, null=True)  # Ej: "Compra #O123" o "Promo Día de la Madre"
    config = models.ForeignKey(PointsConfig, on_delete=models.SET_NULL, null=True, blank=True)  # Configuración usada
    tags = models.ManyToManyField(Tag, blank=True)

    def __str__(self):
        return f"{self.points} points for {self.customer.name}"

# Señal para calcular puntos al completar pedido (en post_save de Order)
@receiver(post_save, sender=Order)
def award_points_on_completion(sender, instance, **kwargs):
    if instance.status != 'completed':
        return
    if CustomerPoints.objects.filter(reason=f"Compra #{instance.order_number}").exists():
        return

    today = date.today()
    
    # 1. Buscar promo activa con fecha
    promo_config = PointsConfig.objects.filter(
        is_active=True,
        start_date__lte=today,
        end_date__gte=today
    ).order_by('-multiplier').first()

    # 2. Si hay promo, usarla
    if promo_config:
        config = promo_config
    else:
        # 3. Si no, usar la configuración predeterminada
        config = PointsConfig.objects.filter(is_default=True, is_active=True).first()
        if not config:
            # 4. Fallback: la primera activa sin fecha
            config = PointsConfig.objects.filter(is_active=True, start_date__isnull=True).first()

    if not config:
        logger.warning("No hay configuración de puntos activa")
        return

    # --- Cálculo de puntos ---
    total = instance.total_amount
    base_points = int(total // config.amount_threshold) * config.points_per_amount
    points = int(base_points * config.multiplier)

    CustomerPoints.objects.create(
        customer=instance.customer,
        points=points,
        reason=f"Compra #{instance.order_number}",
        config=config
    )
    logger.info(f"{points} puntos otorgados ({config.name}) por {instance.order_number}")

class ProductionQueue(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    queue_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES)
    delivery_date = models.DateField()
    position = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('queue_type', 'delivery_date', 'position')
        ordering = ['delivery_date', 'queue_type', 'position']

class Invoice(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(max_length=10, unique=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
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
            last_invoice = Invoice.objects.order_by('-id').first()
            if last_invoice and last_invoice.invoice_number:
                last_number = int(last_invoice.invoice_number[1:])
                self.invoice_number = f"I{last_number + 1:08d}"
            else:
                self.invoice_number = "I00000001"
        self.is_urgent = self.order.order_type == 'urgent'
        self.total_amount = self.order.total_amount
        super().save(*args, **kwargs)