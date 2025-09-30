# backend\api\serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, Customer, Order, OrderItem, UniformDetail, Player, OrderEvent, Promotion, CustomerPoints, ProductionQueue, Invoice, Payment
from products.models import Product, ProductType
from django.utils import timezone
from datetime import timedelta
import logging
from django.db import models, transaction
from rest_framework.exceptions import ValidationError
from decimal import Decimal
import json

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)

def json_safe_dump(obj):
    def default(o):
        return str(o)
    try:
        return json.dumps(obj, default=default, indent=2)
    except Exception as e:
        return f"Error dumping: {str(e)} - {str(obj)}"

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['staff_status', 'phone_number', 'address', 'profile_picture']

class UserSerializer(serializers.ModelSerializer):
    userprofile = UserProfileSerializer(required=False)
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'userprofile']
        extra_kwargs = {
            'password': {'write_only': True},
            'username': {'read_only': True}
        }

    def update(self, instance, validated_data):
        logger.debug(f"Updating user {instance.username} with data: {json_safe_dump(validated_data)}")
        userprofile_data = validated_data.pop('userprofile', {})
        userprofile = instance.userprofile
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.email = validated_data.get('email', instance.email)
        instance.save()
        userprofile.staff_status = userprofile_data.get('staff_status', userprofile.staff_status)
        userprofile.phone_number = userprofile_data.get('phone_number', userprofile.phone_number)
        userprofile.address = userprofile_data.get('address', userprofile.address)
        userprofile.profile_picture = userprofile_data.get('profile_picture', userprofile.profile_picture)
        userprofile.save()
        logger.info(f"User {instance.username} updated successfully")
        return instance

class CustomerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Customer
        fields = ['id', 'name', 'id_type', 'id_number', 'email', 'phone_number', 'address', 'company', 'tipo_contacto', 'created_at', 'updated_at', 'user']

    def validate_id_number(self, value):
        logger.debug(f"Validating id_number: {value}")
        if self.instance is None and Customer.objects.filter(id_number=value).exists():
            logger.error(f"id_number {value} already registered")
            raise serializers.ValidationError("El número de identificación ya está registrado.")
        return value

class PlayerSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Player
        fields = ['id', 'first_name', 'last_name', 'number', 'size', 'gender', 'observaciones', 'variaciones']

    def validate(self, data):
        logger.info(f"Validating Player with data:\n{json_safe_dump(data)}")
        required_fields = ['first_name', 'last_name', 'number', 'size', 'gender']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            logger.error(f"Player validation failed: Missing required fields {missing_fields}")
            raise ValidationError(f"Todos los campos requeridos ({', '.join(missing_fields)}) deben estar completos.")
        return data

class UniformDetailSerializer(serializers.ModelSerializer):
    players = PlayerSerializer(many=True, required=False)
    player_uniform_photo = serializers.ImageField(required=False, allow_null=True)
    goalkeeper_uniform_photo = serializers.ImageField(required=False, allow_null=True)
    neck_photo = serializers.ImageField(required=False, allow_null=True)
    pants_photo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = UniformDetail
        fields = [
            'shirt_quantity', 'shirt_fabric', 'pants_quantity', 'pants_fabric',
            'polo_quantity', 'polo_fabric', 'bag_quantity', 'bag_fabric',
            'sponsorships', 'player_uniform_photo', 'goalkeeper_uniform_photo',
            'neck_photo', 'pants_photo', 'players'
        ]

    def validate(self, data):
        logger.info(f"Validating UniformDetail with data:\n{json_safe_dump(data)}")
        return data

    def create(self, validated_data):
        logger.debug(f"Creating UniformDetail with data:\n{json_safe_dump(validated_data)}")
        players_data = validated_data.pop('players', [])
        uniform_detail = UniformDetail.objects.create(**validated_data)
        for player_data in players_data:
            logger.info(f"Creating Player with data:\n{json_safe_dump(player_data)}")
            Player.objects.create(uniform_detail=uniform_detail, **player_data)
        logger.info(f"UniformDetail created successfully for order")
        return uniform_detail

    def update(self, instance, validated_data):
        logger.info(f"Updating UniformDetail with data:\n{json_safe_dump(validated_data)}")
        players_data = validated_data.pop('players', None)
        logger.info(f"Players data for update:\n{json_safe_dump(players_data)}")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if players_data is not None:
            # Update or create players based on ID
            existing_player_ids = {player.id for player in instance.players.all()}
            new_player_ids = {player_data.get('id') for player_data in players_data if player_data.get('id') is not None}
            # Delete players not in the new data
            deleted_count = instance.players.exclude(id__in=new_player_ids).delete()[0]
            logger.info(f"Deleted {deleted_count} players not in new data")
            for player_data in players_data:
                player_id = player_data.pop('id', None)
                if player_id and player_id in existing_player_ids:
                    # Update existing player
                    player = instance.players.get(id=player_id)
                    logger.info(f"Updating Player {player_id} with data:\n{json_safe_dump(player_data)}")
                    for attr, value in player_data.items():
                        setattr(player, attr, value)
                    player.save()
                else:
                    # Create new player
                    logger.info(f"Creating new Player with data:\n{json_safe_dump(player_data)}")
                    Player.objects.create(uniform_detail=instance, **player_data)
        logger.info(f"UniformDetail updated successfully with {len(players_data or [])} players")
        return instance

class OrderItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), required=False, allow_null=True)
    product_type = serializers.PrimaryKeyRelatedField(queryset=ProductType.objects.all(), required=False, allow_null=True)
    design_file = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_type', 'quantity', 'unit_price', 'design_file']

    def validate(self, data):
        logger.info(f"Validating OrderItem with data:\n{json_safe_dump(data)}")
        product = data.get('product')
        product_type = data.get('product_type')
        if not product and not product_type:
            logger.error("OrderItem validation failed: Must specify product or product_type")
            raise ValidationError("Debe especificar un producto o tipo de producto.")
        if product and product_type:
            logger.error("OrderItem validation failed: Cannot specify both product and product_type")
            raise ValidationError("No puede especificar tanto un producto como un tipo de producto.")
        if product_type and not data.get('design_file'):
            logger.error("OrderItem validation failed: Design file required for custom products")
            raise ValidationError("Se requiere un archivo de diseño para productos personalizados.")
        if data.get('quantity', 0) < 1:
            logger.error("OrderItem validation failed: Quantity must be at least 1")
            raise ValidationError("La cantidad debe ser mayor o igual a 1.")
        if data.get('unit_price', 0) <= 0:
            logger.error("OrderItem validation failed: Unit price must be greater than 0")
            raise ValidationError("El precio unitario debe ser mayor a 0.")
        return data

class OrderEventSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    class Meta:
        model = OrderEvent
        fields = ['id', 'event_type', 'user', 'timestamp', 'document']

    def validate_event_type(self, value):
        logger.debug(f"Validating event_type: {value}")
        if value not in dict(OrderEvent.EVENT_TYPES):
            logger.error(f"Invalid event_type: {value}")
            raise ValidationError("Tipo de evento inválido.")
        return value

    def validate(self, data):
        logger.debug(f"Validating OrderEvent with data:\n{json_safe_dump(data)}")
        if 'document' in data and data['document']:
            allowed_types = ['image/jpeg', 'image/png', 'application/pdf']
            if data['document'].content_type not in allowed_types:
                logger.error(f"Invalid document type: {data['document'].content_type}")
                raise ValidationError(f"Tipo de archivo no permitido. Permitidos: {', '.join(allowed_types)}")
            max_size = 5 * 1024 * 1024  # 5MB
            if data['document'].size > max_size:
                logger.error(f"Document size exceeds limit: {data['document'].size}")
                raise ValidationError(f"El archivo excede el límite de {max_size / (1024 * 1024)}MB")
        return data

class PromotionSerializer(serializers.ModelSerializer):
    products = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), many=True, required=False)
    class Meta:
        model = Promotion
        fields = ['id', 'name', 'description', 'min_amount', 'discount', 'products', 'created_at']

class CustomerPointsSerializer(serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    class Meta:
        model = CustomerPoints
        fields = ['id', 'customer', 'points', 'earned_at']

class ProductionQueueSerializer(serializers.ModelSerializer):
    order = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all())
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    customer_name = serializers.CharField(source='order.customer.name', read_only=True)
    status = serializers.CharField(source='order.status', read_only=True)
    items = serializers.SerializerMethodField()

    class Meta:
        model = ProductionQueue
        fields = ['id', 'order', 'order_number', 'customer_name', 'queue_type', 'delivery_date', 'created_at', 'status', 'items']

    def get_items(self, obj):
        logger.debug(f"Getting items for ProductionQueue: {obj.id}")
        items = obj.order.items.all()
        return [
            {
                'product_name': item.product.name if item.product else item.product_type.name,
                'quantity': item.quantity,
                'unit_price': str(item.unit_price)
            } for item in items
        ]

class OrderSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    customer_id = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), source='customer', write_only=True)
    created_by = serializers.ReadOnlyField(source='created_by.username')
    items = OrderItemSerializer(many=True, required=False)
    uniform_detail = UniformDetailSerializer(required=False, allow_null=True)
    events = OrderEventSerializer(many=True, read_only=True)
    use_points = serializers.BooleanField(write_only=True, default=False)
    payment_50_date = serializers.DateField(required=False, allow_null=True)
    design_confirmation_date = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'pedido_number', 'customer', 'customer_id', 'created_by',
            'created_at', 'updated_at', 'order_date', 'payment_50_date',
            'design_confirmation_date', 'delivery_date', 'status', 'order_type',
            'items', 'uniform_detail', 'events', 'use_points'
        ]

    def calculate_delivery_date(self, items, payment_50_date, manual_delivery_date=None):
        logger.debug(f"Calculating delivery date with items:\n{json_safe_dump(items)}\npayment_50_date: {payment_50_date}, manual_delivery_date: {manual_delivery_date}")
        from datetime import datetime
        base_date = payment_50_date or timezone.now().date()
        max_delivery_days = 0
        product_type_quantities = {}

        # Calculate total quantities per product type and max delivery time
        for item in items:
            product_type = item.get('product_type') or (item.get('product').product_type if item.get('product') else None)
            if product_type:
                product_type_id = product_type.id
                quantity = item.get('quantity', 0)
                product_type_quantities[product_type_id] = product_type_quantities.get(product_type_id, 0) + quantity
                max_delivery_days = max(max_delivery_days, product_type.delivery_time_days)

        # If manual delivery date is provided, use it if valid
        if manual_delivery_date:
            proposed_date = manual_delivery_date
            if proposed_date < base_date:
                logger.error(f"Invalid delivery date: {proposed_date} is before base_date {base_date}")
                raise serializers.ValidationError("La fecha de entrega no puede ser anterior a la fecha base.")
        else:
            proposed_date = base_date + timedelta(days=max_delivery_days)

        # Check production capacity
        while True:
            capacity_ok = True
            for product_type_id, requested_quantity in product_type_quantities.items():
                product_type = ProductType.objects.get(id=product_type_id)
                existing_queues = ProductionQueue.objects.filter(
                    delivery_date=proposed_date,
                    order__items__product_type=product_type
                ).distinct()
                existing_quantity = sum(
                    item.quantity for queue in existing_queues
                    for item in queue.order.items.filter(product_type=product_type)
                )
                total_quantity = existing_quantity + requested_quantity
                if total_quantity > product_type.daily_production_capacity:
                    logger.warning(f"Capacity exceeded for {product_type.name} on {proposed_date}: {total_quantity} > {product_type.daily_production_capacity}")
                    capacity_ok = False
                    break
            if capacity_ok:
                logger.debug(f"Delivery date calculated: {proposed_date}")
                return proposed_date
            proposed_date += timedelta(days=1)

    def validate(self, data):
        logger.info(f"Validating Order with data:\n{json_safe_dump(data)}")
        items = data.get('items')
        status = data.get('status')
        payment_50_date = data.get('payment_50_date')
        delivery_date = data.get('delivery_date')
        is_partial = self.partial

        # Only enforce items requirement for creation
        if not is_partial and not items:
            logger.error("No items provided in order creation")
            raise serializers.ValidationError("Se requiere al menos un ítem en el pedido.")

        if status != 'in_progress':
            data.pop('payment_50_date', None)
            data.pop('design_confirmation_date', None)
            data['pedido_number'] = None

        # Calculate or validate delivery date only if items are provided
        if items and isinstance(items, list) and len(items) > 0:
            calculated_delivery_date = self.calculate_delivery_date(
                items=items,
                payment_50_date=payment_50_date or timezone.now().date(),
                manual_delivery_date=delivery_date
            )
            if not delivery_date:
                data['delivery_date'] = calculated_delivery_date
            else:
                # Validate manual delivery date
                product_type_quantities = {}
                for item in items:
                    product_type = item.get('product_type') or (item.get('product').product_type if item.get('product') else None)
                    if product_type:
                        product_type_id = product_type.id
                        quantity = item.get('quantity', 0)
                        product_type_quantities[product_type_id] = product_type_quantities.get(product_type_id, 0) + quantity
                for product_type_id, requested_quantity in product_type_quantities.items():
                    product_type = ProductType.objects.get(id=product_type_id)
                    existing_queues = ProductionQueue.objects.filter(
                        delivery_date=delivery_date,
                        order__items__product_type=product_type
                    ).distinct()
                    existing_quantity = sum(
                        item.quantity for queue in existing_queues
                        for item in queue.order.items.filter(product_type=product_type)
                    )
                    total_quantity = existing_quantity + requested_quantity
                    if total_quantity > product_type.daily_production_capacity:
                        logger.error(f"Capacity exceeded for {product_type.name} on {delivery_date}: {total_quantity} > {product_type.daily_production_capacity}")
                        raise serializers.ValidationError(
                            f"La cantidad solicitada ({total_quantity}) para {product_type.name} excede la capacidad diaria de producción ({product_type.daily_production_capacity}) para la fecha {delivery_date}."
                        )

        logger.debug(f"Order validation passed with data:\n{json_safe_dump(data)}")
        return data

    def create(self, validated_data):
        logger.debug(f"Creating Order with validated data:\n{json_safe_dump(validated_data)}")
        with transaction.atomic():
            items_data = validated_data.pop('items')
            uniform_detail_data = validated_data.pop('uniform_detail', None)
            use_points = validated_data.pop('use_points', False)
            validated_data['pedido_number'] = None
            order = Order.objects.create(**validated_data)
            total_price = Decimal('0')
            applicable_promotions = []
            original_totals = []
            for item_data in items_data:
                product = item_data.get('product')
                product_type = item_data.get('product_type')
                quantity = item_data.get('quantity')
                unit_price = item_data.get('unit_price')
                if unit_price is None:
                    if product:
                        unit_price = product.product_type.base_price + product.additional_price
                    elif product_type:
                        unit_price = product_type.base_price
                    item_data['unit_price'] = unit_price
                item_total = Decimal(str(unit_price)) * quantity
                total_price += item_total
                original_totals.append(item_total)
                promotions = Promotion.objects.filter(
                    models.Q(min_amount__lte=item_total) | models.Q(products=product)
                ).distinct()
                applicable_promotions.extend(promotions)
            best_discount = Decimal('0')
            best_promotion = None
            for promotion in set(applicable_promotions):
                if promotion.discount > best_discount:
                    best_discount = promotion.discount
                    best_promotion = promotion
            if best_promotion:
                total_price *= (Decimal('1') - best_discount / Decimal('100'))
            customer = validated_data['customer']
            if use_points:
                points_record = CustomerPoints.objects.filter(customer=customer).aggregate(total_points=models.Sum('points'))
                available_points = points_record.get('total_points', 0) or 0
                points_value = min(available_points * Decimal('0.1'), total_price)
                total_price -= points_value
                if points_value > Decimal('0'):
                    CustomerPoints.objects.create(customer=customer, points=-int(points_value / Decimal('0.1')))
            if total_price != sum(original_totals):
                for i, item_data in enumerate(items_data):
                    adjusted_item_total = original_totals[i] * total_price / sum(original_totals)
                    item_data['unit_price'] = adjusted_item_total / item_data['quantity']
            for item_data in items_data:
                item_data.pop('id', None)  # Remove id if present, since create
                logger.info(f"Creating OrderItem with data:\n{json_safe_dump(item_data)}")
                OrderItem.objects.create(order=order, **item_data)
            if uniform_detail_data:
                UniformDetailSerializer().create({**uniform_detail_data, 'order': order})
            logger.info(f"Order {order.order_number} created successfully")
            return order

    def update(self, instance, validated_data):
        logger.info(f"Updating Order {instance.order_number} with full validated data:\n{json_safe_dump(validated_data)}")
        with transaction.atomic():
            items_data = validated_data.pop('items', None)
            uniform_detail_data = validated_data.pop('uniform_detail', None)
            use_points = validated_data.pop('use_points', False)
            if validated_data.get('status') != 'in_progress':
                validated_data['pedido_number'] = None
                validated_data.pop('payment_50_date', None)
                validated_data.pop('design_confirmation_date', None)
            logger.info(f"Updating Order {instance.order_number} with top-level validated data:\n{json_safe_dump(validated_data)}")
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            if items_data is not None:
                logger.info(f"Processing items update:\n{json_safe_dump(items_data)}")
                total_price = Decimal('0')
                applicable_promotions = []
                original_totals = []
                for item_data in items_data:
                    product = item_data.get('product')
                    product_type = item_data.get('product_type')
                    quantity = item_data.get('quantity')
                    unit_price = item_data.get('unit_price')
                    if unit_price is None:
                        if product:
                            unit_price = product.product_type.base_price + product.additional_price
                        elif product_type:
                            unit_price = product_type.base_price
                        item_data['unit_price'] = unit_price
                    item_total = Decimal(str(unit_price)) * quantity
                    total_price += item_total
                    original_totals.append(item_total)
                    promotions = Promotion.objects.filter(
                        models.Q(min_amount__lte=item_total) | models.Q(products=product)
                    ).distinct()
                    applicable_promotions.extend(promotions)
                best_discount = Decimal('0')
                best_promotion = None
                for promotion in set(applicable_promotions):
                    if promotion.discount > best_discount:
                        best_discount = promotion.discount
                        best_promotion = promotion
                if best_promotion:
                    total_price *= (Decimal('1') - best_discount / Decimal('100'))
                customer = instance.customer
                if use_points:
                    points_record = CustomerPoints.objects.filter(customer=customer).aggregate(total_points=models.Sum('points'))
                    available_points = points_record.get('total_points', 0) or 0
                    points_value = min(available_points * Decimal('0.1'), total_price)
                    total_price -= points_value
                    if points_value > Decimal('0'):
                        CustomerPoints.objects.create(customer=customer, points=-int(points_value / Decimal('0.1')))
                if total_price != sum(original_totals):
                    for i, item_data in enumerate(items_data):
                        adjusted_item_total = original_totals[i] * total_price / sum(original_totals)
                        item_data['unit_price'] = adjusted_item_total / item_data['quantity']
                # Now update/create/delete items
                existing_item_ids = {item.id for item in instance.items.all()}
                new_item_ids = {item_data.get('id') for item_data in items_data if item_data.get('id') is not None}
                deleted_count = instance.items.exclude(id__in=new_item_ids).delete()[0]
                logger.info(f"Deleted {deleted_count} items not in new data")
                for item_data in items_data:
                    item_id = item_data.pop('id', None)
                    if item_id and item_id in existing_item_ids:
                        item = instance.items.get(id=item_id)
                        logger.info(f"Updating OrderItem {item_id} with data:\n{json_safe_dump(item_data)}")
                        for attr, value in item_data.items():
                            setattr(item, attr, value)
                        item.save()
                    else:
                        logger.info(f"Creating new OrderItem with data:\n{json_safe_dump(item_data)}")
                        OrderItem.objects.create(order=instance, **item_data)
            if uniform_detail_data is not None:
                logger.info(f"Processing uniform_detail update:\n{json_safe_dump(uniform_detail_data)}")
                if instance.uniform_detail:
                    UniformDetailSerializer().update(instance.uniform_detail, uniform_detail_data)
                else:
                    UniformDetailSerializer().create({**uniform_detail_data, 'order': instance})
            if instance.status == 'in_progress':
                instance.assign_pedido_number()
            else:
                instance.pedido_number = None
                instance.save(update_fields=['pedido_number'])
            logger.info(f"Order {instance.order_number} updated successfully")
            return instance

    def validate_delivery_date(self, value):
        logger.debug(f"Validating delivery_date: {value}")
        if self.instance and self.instance.delivery_date != value:
            user = self.context['request'].user
            try:
                user_profile = user.userprofile
            except UserProfile.DoesNotExist:
                logger.error(f"User {user.username} has no UserProfile")
                raise serializers.ValidationError("User has no profile.")
            if user_profile.staff_status != 'administrator':
                logger.error(f"User {user.username} not authorized to change delivery_date")
                raise serializers.ValidationError("Solo los administradores pueden modificar la fecha de entrega.")
        return value

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class EmailSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=200)
    message = serializers.CharField(max_length=4000)
    from_email = serializers.EmailField()
    recipient_list = serializers.CharField()

    def validate_recipient_list(self, value):
        logger.debug(f"Validating recipient_list: {value}")
        return [email.strip() for email in value.split(',')]

class InvoiceSerializer(serializers.ModelSerializer):
    order = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all())
    class Meta:
        model = Invoice
        fields = [
            'id', 'order', 'invoice_number', 'total_amount', 'tax', 'issued_date',
            'signature_field', 'reviewed_date', 'packed_date', 'delivered_date', 'is_urgent'
        ]

class PaymentSerializer(serializers.ModelSerializer):
    order = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all())
    class Meta:
        model = Payment
        fields = ['id', 'order', 'amount', 'payment_date', 'payment_type', 'reference_document']