from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, Customer, Order, OrderItem, UniformDetail, Player, OrderEvent, Promotion, CustomerPoints, ProductionQueue, Invoice, Payment
from products.models import Product, ProductType
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

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

        return instance

class CustomerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Customer
        fields = ['id', 'name', 'id_type', 'id_number', 'email', 'phone_number', 'address', 'company', 'tipo_contacto', 'created_at', 'updated_at', 'user']

    def validate_id_number(self, value):
        if self.instance is None and Customer.objects.filter(id_number=value).exists():
            raise serializers.ValidationError("El número de identificación ya está registrado.")
        return value

class PlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = ['id', 'first_name', 'last_name', 'number', 'size', 'gender']

class UniformDetailSerializer(serializers.ModelSerializer):
    players = PlayerSerializer(many=True, required=False)

    class Meta:
        model = UniformDetail
        fields = [
            'id', 'shirt_quantity', 'shirt_fabric', 'pants_quantity', 'pants_fabric',
            'polo_quantity', 'polo_fabric', 'bag_quantity', 'bag_fabric',
            'player_uniform_photo', 'goalkeeper_uniform_photo', 'neck_photo', 'pants_photo',
            'sponsorships', 'players'
        ]

    def create(self, validated_data):
        players_data = validated_data.pop('players', [])
        uniform_detail = UniformDetail.objects.create(**validated_data)
        for player_data in players_data:
            Player.objects.create(uniform_detail=uniform_detail, **player_data)
        return uniform_detail

    def update(self, instance, validated_data):
        players_data = validated_data.pop('players', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        instance.players.all().delete()
        for player_data in players_data:
            Player.objects.create(uniform_detail=instance, **player_data)
        return instance

class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), required=False, allow_null=True)
    product_type = serializers.PrimaryKeyRelatedField(queryset=ProductType.objects.all(), required=False, allow_null=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_type', 'design_file', 'quantity', 'unit_price']

    def validate(self, data):
        if not data.get('product') and not data.get('product_type'):
            raise serializers.ValidationError("Se debe especificar un producto o un tipo de producto.")
        if data.get('product') and data.get('product_type'):
            raise serializers.ValidationError("No se puede especificar un producto y un tipo de producto al mismo tiempo.")
        if data.get('product_type') and not data.get('design_file'):
            raise serializers.ValidationError("Se requiere un archivo de diseño para productos personalizados.")
        return data

class OrderEventSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = OrderEvent
        fields = ['id', 'event_type', 'user', 'timestamp', 'document']

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

    class Meta:
        model = ProductionQueue
        fields = ['id', 'order', 'queue_type', 'delivery_date', 'created_at']

class OrderSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    customer_id = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), source='customer', write_only=True)
    created_by = serializers.ReadOnlyField(source='created_by.username')
    items = OrderItemSerializer(many=True)
    uniform_detail = UniformDetailSerializer(required=False, allow_null=True)
    events = OrderEventSerializer(many=True, read_only=True)
    use_points = serializers.BooleanField(write_only=True, default=False)  # New field to indicate if points should be used

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'pedido_number', 'customer', 'customer_id', 'created_by',
            'created_at', 'updated_at', 'order_date', 'payment_50_date',
            'design_confirmation_date', 'delivery_date', 'status', 'order_type',
            'items', 'uniform_detail', 'events', 'use_points'
        ]

    def validate(self, data):
        delivery_date = data.get('delivery_date')
        items = data.get('items', [])
        if delivery_date:
            # Calculate total quantity per product type for the given delivery date
            product_type_quantities = {}
            for item in items:
                product_type = item.get('product_type')
                if product_type:
                    product_type_id = product_type.id
                    quantity = item.get('quantity', 0)
                    product_type_quantities[product_type_id] = product_type_quantities.get(product_type_id, 0) + quantity
                elif item.get('product'):
                    product_type_id = item['product'].product_type.id
                    quantity = item.get('quantity', 0)
                    product_type_quantities[product_type_id] = product_type_quantities.get(product_type_id, 0) + quantity

            # Check production capacity for each product type
            for product_type_id, requested_quantity in product_type_quantities.items():
                product_type = ProductType.objects.get(id=product_type_id)
                # Get existing orders for the same delivery date and product type
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
                    raise serializers.ValidationError(
                        f"La cantidad solicitada ({total_quantity}) para {product_type.name} excede la capacidad diaria de producción ({product_type.daily_production_capacity}) para la fecha {delivery_date}."
                    )
        return data

    def create(self, validated_data):
        logger.debug(f"Datos recibidos en ProductSerializer.create: {validated_data}")
        items_data = validated_data.pop('items')
        uniform_detail_data = validated_data.pop('uniform_detail', None)
        use_points = validated_data.pop('use_points', False)
        order = Order.objects.create(**validated_data)

        # Apply promotions and points
        total_price = 0
        applicable_promotions = []
        for item_data in items_data:
            product = item_data.get('product')
            product_type = item_data.get('product_type')
            quantity = item_data.get('quantity')
            unit_price = item_data.get('unit_price')

            # Calculate base price
            if product:
                unit_price = product.product_type.base_price + product.additional_price
            elif product_type:
                unit_price = product_type.base_price
            item_total = unit_price * quantity
            total_price += item_total

            # Find applicable promotions
            promotions = Promotion.objects.filter(
                models.Q(min_amount__lte=item_total) | models.Q(products=product)
            ).distinct()
            applicable_promotions.extend(promotions)

        # Apply the best promotion (highest discount)
        best_discount = 0
        best_promotion = None
        for promotion in applicable_promotions:
            if promotion.discount > best_discount:
                best_discount = promotion.discount
                best_promotion = promotion
        if best_promotion:
            total_price *= (1 - best_promotion.discount / 100)

        # Apply points if requested
        customer = validated_data['customer']
        if use_points:
            points_record = CustomerPoints.objects.filter(customer=customer).aggregate(total_points=models.Sum('points'))
            available_points = points_record.get('total_points', 0) or 0
            points_value = min(available_points * 0.1, total_price)  # 1 point = 0.1 currency unit
            total_price -= points_value
            if points_value > 0:
                CustomerPoints.objects.create(customer=customer, points=-int(points_value / 0.1))

        # Update item prices
        for item_data in items_data:
            product = item_data.get('product')
            product_type = item_data.get('product_type')
            quantity = item_data.get('quantity')
            unit_price = item_data.get('unit_price')
            if product:
                unit_price = product.product_type.base_price + product.additional_price
            elif product_type:
                unit_price = product_type.base_price
            # Adjust unit price based on applied discounts
            item_total = unit_price * quantity
            adjusted_item_total = item_total * (total_price / sum(item['quantity'] * (item['product'].product_type.base_price + item['product'].additional_price if item['product'] else item['product_type'].base_price) for item in items_data))
            item_data['unit_price'] = adjusted_item_total / quantity
            OrderItem.objects.create(order=order, **item_data)

        if uniform_detail_data:
            UniformDetailSerializer().create({**uniform_detail_data, 'order': order})
        order.assign_pedido_number()
        return order

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', [])
        uniform_detail_data = validated_data.pop('uniform_detail', None)
        use_points = validated_data.pop('use_points', False)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Apply promotions and points
        total_price = 0
        applicable_promotions = []
        for item_data in items_data:
            product = item_data.get('product')
            product_type = item_data.get('product_type')
            quantity = item_data.get('quantity')
            unit_price = item_data.get('unit_price')

            # Calculate base price
            if product:
                unit_price = product.product_type.base_price + product.additional_price
            elif product_type:
                unit_price = product_type.base_price
            item_total = unit_price * quantity
            total_price += item_total

            # Find applicable promotions
            promotions = Promotion.objects.filter(
                models.Q(min_amount__lte=item_total) | models.Q(products=product)
            ).distinct()
            applicable_promotions.extend(promotions)

        # Apply the best promotion
        best_discount = 0
        best_promotion = None
        for promotion in applicable_promotions:
            if promotion.discount > best_discount:
                best_discount = promotion.discount
                best_promotion = promotion
        if best_promotion:
            total_price *= (1 - best_promotion.discount / 100)

        # Apply points if requested
        customer = instance.customer
        if use_points:
            points_record = CustomerPoints.objects.filter(customer=customer).aggregate(total_points=models.Sum('points'))
            available_points = points_record.get('total_points', 0) or 0
            points_value = min(available_points * 0.1, total_price)
            total_price -= points_value
            if points_value > 0:
                CustomerPoints.objects.create(customer=customer, points=-int(points_value / 0.1))

        # Update items
        instance.items.all().delete()
        for item_data in items_data:
            product = item_data.get('product')
            product_type = item_data.get('product_type')
            quantity = item_data.get('quantity')
            unit_price = item_data.get('unit_price')
            if product:
                unit_price = product.product_type.base_price + product.additional_price
            elif product_type:
                unit_price = product_type.base_price
            item_total = unit_price * quantity
            adjusted_item_total = item_total * (total_price / sum(item['quantity'] * (item['product'].product_type.base_price + item['product'].additional_price if item['product'] else item['product_type'].base_price) for item in items_data))
            item_data['unit_price'] = adjusted_item_total / quantity
            OrderItem.objects.create(order=instance, **item_data)

        if uniform_detail_data:
            if instance.uniform_detail:
                UniformDetailSerializer().update(instance.uniform_detail, uniform_detail_data)
            else:
                UniformDetailSerializer().create({**uniform_detail_data, 'order': instance})

        instance.assign_pedido_number()
        return instance
    
    def validate_delivery_date(self, value):
        if self.instance and self.instance.delivery_date != value:
            user = self.context['request'].user
            user_profile = user.userprofile
            if user_profile.staff_status != 'administrator':
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