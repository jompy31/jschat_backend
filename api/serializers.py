# backend\api\serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, Customer,PointsConfig,  Order, OrderItem, UniformDetail, Player, OrderEvent, Promotion, CustomerPoints, ProductionQueue, Invoice, Payment
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
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), required=False, allow_null=True
    )
    product_type = serializers.PrimaryKeyRelatedField(
        queryset=ProductType.objects.all(), required=False, allow_null=True
    )
    design_file = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_type', 'quantity', 'unit_price', 'design_file']
        extra_kwargs = {
            'unit_price': {'read_only': True}  # Hacer unit_price de solo lectura
        }

    def to_internal_value(self, data):
        logger.debug(f"OrderItemSerializer.to_internal_value() - entrada: {data}")
        data = dict(data)
        data.pop('unit_price', None)

        if 'product' in data and data['product'] not in [None, '']:
            try:
                product_id = int(data['product'])
                data['product'] = Product.objects.get(pk=product_id)
            except (ValueError, TypeError):
                raise ValidationError(f"product debe ser un ID válido: {data['product']}")
            except Product.DoesNotExist:
                raise ValidationError(f"Producto con ID {data['product']} no existe.")

        if 'product_type' in data and data['product_type'] not in [None, '']:
            try:
                pt_id = int(data['product_type'])
                data['product_type'] = ProductType.objects.get(pk=pt_id)
            except (ValueError, TypeError):
                raise ValidationError(f"product_type debe ser un ID válido: {data['product_type']}")
            except ProductType.DoesNotExist:
                raise ValidationError(f"Tipo de producto con ID {data['product_type']} no existe.")

        result = super().to_internal_value(data)
        return result

    def validate(self, data):
        logger.debug(f"OrderItemSerializer.validate() - data: {data}")
        product = data.get('product')
        product_type = data.get('product_type')

        if not product and not product_type:
            raise ValidationError("Debe especificar un producto o tipo de producto.")
        if product and product_type:
            raise ValidationError("No puede especificar ambos.")

        # Solo requerir design_file si product_type está presente
        if product_type and 'design_file' not in data:
            logger.warning("Falta design_file para product_type")
            raise ValidationError("Se requiere archivo de diseño para productos personalizados.")

        if data.get('quantity', 0) < 1:
            raise ValidationError("La cantidad debe ser al menos 1.")

        return data

class OrderEventSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)

    class Meta:
        model = OrderEvent
        fields = ['id', 'event_type', 'user', 'timestamp', 'document', 'amount']

    def validate(self, data):
        logger.debug(f"OrderEventSerializer.validate() - Input data: {json_safe_dump(data)}")
        if data['event_type'] != 'payment' and data.get('amount', 0) != 0:
            logger.error(f"Validation failed: Amount {data.get('amount')} is only valid for 'payment' event_type")
            raise serializers.ValidationError("El monto solo es válido para eventos de pago.")
        logger.info(f"Validation passed for event_type={data['event_type']}, amount={data.get('amount')}")
        return data

    def create(self, validated_data):
        logger.debug(f"OrderEventSerializer.create() - Validated data: {json_safe_dump(validated_data)}")
        event = OrderEvent.objects.create(**validated_data)
        logger.info(f"OrderEvent created: id={event.id}, order={event.order.order_number}, event_type={event.event_type}")
        return event

    def update(self, instance, validated_data):
        logger.debug(f"OrderEventSerializer.update() - Instance id={instance.id}, Validated data: {json_safe_dump(validated_data)}")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        logger.info(f"OrderEvent updated: id={instance.id}, order={instance.order.order_number}, event_type={instance.event_type}")
        return instance
class ProductSerializer(serializers.ModelSerializer):
    total_price = serializers.SerializerMethodField()  # Campo calculado para el precio total

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'design_file', 'additional_price', 'total_price', 'characteristics', 'created_at']

    def get_total_price(self, obj):
        return obj.product_type.base_price + obj.additional_price

class PromotionSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)  # Para la lectura (respuesta GET)
    product_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True,
        source='products'  # Mapear a la relación 'products' del modelo
    )  # Usamos ListField para aceptar una lista de IDs directamente

    class Meta:
        model = Promotion
        fields = ['id', 'name', 'description', 'min_amount', 'discount', 'products', 'product_ids', 'created_at']

    def to_internal_value(self, data):
        """
        Procesar datos crudos entrantes, incluyendo el campo 'products' enviado por el frontend.
        """
        logger.debug(f"PromotionSerializer.to_internal_value() - Raw input data: {json_safe_dump(data)}")
        
        # Si el frontend envía 'products' en lugar de 'product_ids', lo mapeamos manualmente
        if 'products' in data and 'product_ids' not in data:
            data = data.copy()  # Crear una copia mutable
            data['product_ids'] = data.pop('products')  # Renombrar 'products' a 'product_ids'
            logger.debug(f"Renamed 'products' to 'product_ids': {json_safe_dump(data)}")
        
        validated_data = super().to_internal_value(data)
        logger.debug(f"to_internal_value() - Validated data: {json_safe_dump(validated_data)}")
        return validated_data

    def validate(self, data):
        """
        Validar los datos, incluyendo product_ids, y convertir los IDs en instancias de Product.
        """
        logger.debug(f"PromotionSerializer.validate() - Input data: {json_safe_dump(data)}")
        
        # Validar descuento
        if 'discount' in data and (data['discount'] <= 0 or data['discount'] > 100):
            logger.error(f"Validation failed: Discount {data['discount']} must be between 0 and 100")
            raise serializers.ValidationError("El descuento debe estar entre 0 y 100.")
        
        # Validar monto mínimo
        if 'min_amount' in data and data['min_amount'] is not None and data['min_amount'] < 0:
            logger.error(f"Validation failed: min_amount {data['min_amount']} must be non-negative")
            raise serializers.ValidationError("El monto mínimo no puede ser negativo.")
        
        # Validar y convertir product_ids a instancias de Product
        if 'products' in data:
            product_ids = data['products']  # En este punto, 'products' contiene los IDs mapeados desde 'product_ids'
            try:
                # Obtener las instancias de Product correspondientes a los IDs
                products = Product.objects.filter(pk__in=product_ids)
                if len(products) != len(product_ids):
                    missing_ids = set(product_ids) - set(p.pk for p in products)
                    logger.error(f"Validation failed: Invalid product IDs {missing_ids}")
                    raise serializers.ValidationError(f"Los siguientes IDs de productos no existen: {missing_ids}")
                # Reemplazar los IDs en data['products'] con las instancias de Product
                data['products'] = products
                logger.debug(f"Converted product_ids to product instances: {[p.pk for p in products]}")
                logger.info(f"Validated {len(products)} product IDs")
            except Exception as e:
                logger.error(f"Error validating product_ids: {str(e)}")
                raise serializers.ValidationError(f"Error al validar los IDs de productos: {str(e)}")
        else:
            logger.debug("No product_ids provided in validated data")
        
        logger.info(f"Validation passed for promotion: {data.get('name')}")
        return data

    def create(self, validated_data):
        """
        Crear una nueva promoción y asociar productos.
        """
        logger.info(f"PromotionSerializer.create() - Validated data: {json_safe_dump(validated_data)}")
        product_instances = validated_data.pop('products', [])  # Extraer instancias de Product
        logger.debug(f"Extracted products: {[p.pk for p in product_instances] if product_instances else []}")
        
        try:
            # Crear la promoción
            promotion = Promotion.objects.create(**validated_data)
            logger.info(f"Promotion created: id={promotion.id}, name={promotion.name}")
            
            # Asociar productos si existen
            if product_instances:
                promotion.products.set(product_instances)
                logger.info(f"Associated {len(product_instances)} products to promotion {promotion.id}")
            else:
                logger.info(f"No products associated with promotion {promotion.id}")
            
            return promotion
        except Exception as e:
            logger.error(f"Error creating promotion: {str(e)}")
            raise

    def update(self, instance, validated_data):
        """
        Actualizar una promoción existente y sus productos asociados.
        """
        logger.info(f"PromotionSerializer.update() - Instance id={instance.id}, Validated data: {json_safe_dump(validated_data)}")
        product_instances = validated_data.pop('products', None)  # Extraer instancias de Product o None
        logger.debug(f"Extracted products for update: {[p.pk for p in product_instances] if product_instances is not None else None}")
        
        try:
            # Actualizar los campos de la promoción
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            logger.info(f"Promotion updated: id={instance.id}, name={instance.name}")
            
            # Actualizar productos si se proporcionaron
            if product_instances is not None:
                instance.products.set(product_instances)
                logger.info(f"Updated {len(product_instances)} products for promotion {instance.id}")
            else:
                logger.info(f"Product associations unchanged for promotion {instance.id}")
            
            return instance
        except Exception as e:
            logger.error(f"Error updating promotion {instance.id}: {str(e)}")
            raise
class PointsConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointsConfig
        fields = '__all__'

class CustomerPointsSerializer(serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    config = PointsConfigSerializer(read_only=True)
    class Meta:
        model = CustomerPoints
        fields = ['id', 'customer', 'points', 'earned_at', 'reason', 'config']

    def validate_points(self, value):
        if value == 0:
            raise serializers.ValidationError("Los puntos no pueden ser cero.")
        return value

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
    

class PaymentSerializer(serializers.ModelSerializer):
    order = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all())
    class Meta:
        model = Payment
        fields = ['id', 'order', 'amount', 'payment_date', 'payment_type', 'reference_document']

class OrderSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(), source='customer', write_only=True
    )
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), write_only=True, required=False
    )
    created_by_username = serializers.ReadOnlyField(source='created_by.username')
    items = OrderItemSerializer(many=True, read_only=True)  # Agregar items
    uniform_detail = UniformDetailSerializer(required=False, allow_null=True)
    events = OrderEventSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)  # Agregar payments
    use_points = serializers.BooleanField(write_only=True, default=False)
    production_queue = ProductionQueueSerializer(read_only=True, source='productionqueue')
    payment_percentage = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = '__all__'
    
    def validate_delivery_date(self, value):
        logger.debug(f"Validating delivery_date: {value}")
        if value and self.instance:  # Solo validar si se envía delivery_date y es actualización
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

    def calculate_delivery_date(self, order, items_data):
        """
        Calcula la fecha de entrega basada en la capacidad de producción y prioridad.
        """
        if not items_data:
            return None

        base_date = order.order_date or date.today()
        items_by_type = {}
        for item in items_data:
            pt_id = item.get('product_type') or (item.get('product').product_type if item.get('product') else None)
            if not pt_id:
                continue
            items_by_type[pt_id] = items_by_type.get(pt_id, 0) + item.get('quantity', 0)

        if not items_by_type:
            return None

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
        priority = ORDER_TYPE_PRIORITY.get(order.order_type, 4)

        while True:
            conflicting = Order.objects.filter(
                delivery_date=current_date,
                status__in=['in_progress', 'design_pending', 'design_confirmed']
            ).exclude(id=order.id if order.id else None)

            higher_priority = conflicting.filter(
                Q(order_type__in=[k for k, v in ORDER_TYPE_PRIORITY.items() if v <= priority])
            )

            load = {}
            for ord in higher_priority:
                for item in ord.items.all():
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
                logger.info(f"Fecha de entrega calculada: {current_date} para orden")
                return current_date

            current_date += timedelta(days=1)

    def create(self, validated_data):
        logger.info("=== INICIO OrderSerializer.create() ===")
        logger.info(f"validated_data keys: {list(validated_data.keys())}")

        # === 1. OBTENER items, archivos y uniform_detail DEL CONTEXTO ===
        request = self.context['request']
        items_data = self.context.get('parsed_items', [])
        item_files = self.context.get('item_files', {})
        uniform_detail_data = self.context.get('uniform_detail_data')

        logger.info(f"items_data desde context: {len(items_data)} ítems")
        for i, item in enumerate(items_data):
            logger.info(f"  Item {i}: {item}")

        if uniform_detail_data is not None:
            logger.info(f"UniformDetail desde context: {json_safe_dump(uniform_detail_data)}")
            logger.info(f"  Camisetas: {uniform_detail_data.get('shirt_quantity')} | Jugadores: {len(uniform_detail_data.get('players', []))}")
        else:
            logger.info("No se recibió uniform_detail_data en context")

        use_points = validated_data.pop('use_points', False)

        # === 2. CREAR ORDEN ===
        validated_data['created_by'] = request.user
        order = Order.objects.create(**validated_data)
        logger.info(f"Orden creada: {order.order_number}")

        # === 3. GUARDAR ÍTEMS ===
        for idx, item_data in enumerate(items_data):
            logger.info(f"Procesando ítem {idx}: {item_data}")

            if idx in item_files:
                item_data['design_file'] = item_files[idx]
                logger.info(f"  Archivo: {item_files[idx].name}")
            else:
                logger.info(f"  Sin archivo")

            try:
                if 'product' in item_data and item_data['product']:
                    item_data['product'] = Product.objects.get(pk=item_data['product'])
                if 'product_type' in item_data and item_data['product_type']:
                    item_data['product_type'] = ProductType.objects.get(pk=item_data['product_type'])

                order_item = OrderItem.objects.create(order=order, **item_data)
                logger.info(f"  Ítem guardado: {order_item}")
            except Exception as e:
                logger.error(f"  Error al guardar ítem: {e}")
                raise

        # === 4. GUARDAR UNIFORM DETAIL ===
        if uniform_detail_data is not None and any(uniform_detail_data.values()):
            players_data = uniform_detail_data.pop('players', [])
            uniform_detail_data['order'] = order

            try:
                uniform_detail = UniformDetail.objects.create(**uniform_detail_data)
                logger.info(f"UniformDetail creado para orden {order.order_number}")
                logger.info(f"  Cantidad camisetas: {uniform_detail.shirt_quantity}, pantalones: {uniform_detail.pants_quantity}")

                for player_data in players_data:
                    Player.objects.create(uniform_detail=uniform_detail, **player_data)
                logger.info(f"  {len(players_data)} jugadores guardados")
            except Exception as e:
                logger.error(f"Error al crear UniformDetail: {e}")
                raise
        else:
            logger.info("No se creó UniformDetail: datos vacíos o no presentes")

        # === 5. PUNTOS ===
        if use_points and order.customer:
            total = order.total_amount
            points = CustomerPoints.objects.filter(customer=order.customer).aggregate(Sum('points'))['points__sum'] or 0
            discount = min(points * Decimal('0.1'), total)
            if discount > 0:
                CustomerPoints.objects.create(customer=order.customer, points=-int(discount / 0.1))
                logger.info(f"Descuento aplicado: {discount}")

        order.refresh_from_db()
        logger.info(f"ORDEN FINAL: {order.order_number} | ÍTEMS: {order.items.count()} | TOTAL: {order.total_amount}")
        if hasattr(order, 'uniform_detail'):
            logger.info(f"UNIFORME GUARDADO: Camisetas={order.uniform_detail.shirt_quantity} | Jugadores={order.uniform_detail.players.count()}")
        logger.info("=== FIN OrderSerializer.create() ===")
        return order
    
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
    def update(self, instance, validated_data):
        logger.info("=== INICIO OrderSerializer.update() ===")
        items_data = self.context.get('parsed_items', [])
        item_files = self.context.get('item_files', {})
        uniform_detail_data = self.context.get('uniform_detail_data')
        use_points = validated_data.pop('use_points', False)

        # Actualizar campos de la orden
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Actualizar ítems
        if items_data is not None:
            logger.debug(f"Items data: {json_safe_dump(items_data)}")
            existing_item_ids = {item.id for item in instance.items.all()}
            new_item_ids = {item.get('id') for item in items_data if item.get('id') is not None}
            # Eliminar ítems no presentes
            deleted_count = instance.items.exclude(id__in=new_item_ids).delete()[0]
            logger.info(f"Deleted {deleted_count} items not in new data")
            for idx, item_data in enumerate(items_data):
                if idx in item_files:
                    item_data['design_file'] = item_files[idx]
                    logger.info(f"Item {idx} design file: {item_files[idx].name}")
                # Ignorar unit_price si se envió
                item_data.pop('unit_price', None)
                try:
                    # Resolver product y product_type a instancias
                    if 'product' in item_data and item_data['product'] not in [None, '']:
                        try:
                            item_data['product'] = Product.objects.get(pk=item_data['product'])
                        except Product.DoesNotExist:
                            logger.error(f"Product with ID {item_data['product']} does not exist")
                            raise serializers.ValidationError(f"Producto con ID {item_data['product']} no existe.")
                    if 'product_type' in item_data and item_data['product_type'] not in [None, '']:
                        try:
                            item_data['product_type'] = ProductType.objects.get(pk=item_data['product_type'])
                        except ProductType.DoesNotExist:
                            logger.error(f"ProductType with ID {item_data['product_type']} does not exist")
                            raise serializers.ValidationError(f"Tipo de producto con ID {item_data['product_type']} no existe.")
                    item_id = item_data.pop('id', None)
                    if item_id and item_id in existing_item_ids:
                        # Actualizar ítem existente
                        item = instance.items.get(id=item_id)
                        logger.debug(f"Updating item {item_id} with data: {json_safe_dump(item_data)}")
                        for attr, value in item_data.items():
                            setattr(item, attr, value)
                        item.save()
                        logger.info(f"Updated item {item_id}")
                    else:
                        # Crear nuevo ítem
                        item = OrderItem.objects.create(order=instance, **item_data)
                        logger.info(f"Created new item {item.id}")
                except Exception as e:
                    logger.error(f"Error processing item {idx}: {str(e)}")
                    raise

        # Actualizar UniformDetail
        if uniform_detail_data is not None and any(uniform_detail_data.values()):
            logger.debug(f"Uniform detail data: {json_safe_dump(uniform_detail_data)}")
            players_data = uniform_detail_data.pop('players', [])
            try:
                uniform_detail = instance.uniform_detail if hasattr(instance, 'uniform_detail') else None
                if uniform_detail:
                    # Actualizar existente
                    for attr, value in uniform_detail_data.items():
                        setattr(uniform_detail, attr, value)
                    uniform_detail.save()
                    logger.info(f"Updated UniformDetail for order {instance.order_number}")
                else:
                    # Crear nuevo
                    uniform_detail_data['order'] = instance
                    uniform_detail = UniformDetail.objects.create(**uniform_detail_data)
                    logger.info(f"Created UniformDetail for order {instance.order_number}")
                # Actualizar jugadores
                if players_data is not None:
                    existing_player_ids = {player.id for player in uniform_detail.players.all()}
                    new_player_ids = {p.get('id') for p in players_data if p.get('id') is not None}
                    deleted_count = uniform_detail.players.exclude(id__in=new_player_ids).delete()[0]
                    logger.info(f"Deleted {deleted_count} players not in new data")
                    for player_data in players_data:
                        player_id = player_data.pop('id', None)
                        if player_id and player_id in existing_player_ids:
                            player = uniform_detail.players.get(id=player_id)
                            for attr, value in player_data.items():
                                setattr(player, attr, value)
                            player.save()
                            logger.info(f"Updated player {player_id}")
                        else:
                            Player.objects.create(uniform_detail=uniform_detail, **player_data)
                            logger.info(f"Created new player")
            except Exception as e:
                logger.error(f"Error updating UniformDetail: {e}")
                raise

        # Manejar puntos
        if use_points and instance.customer:
            total = instance.total_amount
            points = CustomerPoints.objects.filter(customer=instance.customer).aggregate(Sum('points'))['points__sum'] or 0
            discount = min(points * Decimal('0.1'), total)
            if discount > 0:
                CustomerPoints.objects.create(customer=instance.customer, points=-int(discount / 0.1))
                logger.info(f"Applied discount: {discount}")

        instance.refresh_from_db()
        logger.info(f"ORDER UPDATED: {instance.order_number} | ITEMS: {instance.items.count()} | TOTAL: {instance.total_amount}")
        if hasattr(instance, 'uniform_detail'):
            logger.info(f"UNIFORM UPDATED: Shirts={instance.uniform_detail.shirt_quantity} | Players={instance.uniform_detail.players.count()}")
        logger.info("=== FIN OrderSerializer.update() ===")
        return instance

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

# === DASHBOARD SERIALIZERS ===
class DashboardOrderSummarySerializer(serializers.Serializer):
    order_number = serializers.CharField()
    pedido_number = serializers.CharField(allow_null=True)
    customer_name = serializers.CharField(source='customer.name')
    customer_email = serializers.CharField(source='customer.email', allow_null=True)
    order_type = serializers.CharField()
    status = serializers.CharField()
    order_date = serializers.DateField(allow_null=True)
    delivery_date = serializers.DateField(allow_null=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_amount = serializers.SerializerMethodField()
    payment_percentage = serializers.FloatField()
    days_to_delivery = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    priority_level = serializers.SerializerMethodField()

    def get_pending_amount(self, obj):
        return round(obj.total_amount - obj.paid_amount, 2)

    def get_days_to_delivery(self, obj):
        if not obj.delivery_date:
            return None
        delta = obj.delivery_date - (date.today() if not obj.order_date else obj.order_date)
        return delta.days

    def get_is_overdue(self, obj):
        if obj.status in ['in_progress', 'design_pending', 'design_confirmed'] and obj.delivery_date:
            return obj.delivery_date < date.today()
        return False

    def get_priority_level(self, obj):
        return ORDER_TYPE_PRIORITY.get(obj.order_type, 4)


class DashboardProductionDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    total_orders = serializers.IntegerField()
    express = serializers.IntegerField()
    urgent = serializers.IntegerField()
    normal = serializers.IntegerField()
    personalizado = serializers.IntegerField()
    capacity_load = serializers.SerializerMethodField()
    product_types = serializers.SerializerMethodField()

    def get_capacity_load(self, obj):
        total = sum([obj['express'], obj['urgent'], obj['normal'], obj['personalizado']])
        return round((total / max(obj['capacity'], 1)) * 100, 2) if obj['capacity'] else 0

    def get_product_types(self, obj):
        return obj['product_types']


class DashboardProductPerformanceSerializer(serializers.Serializer):
    product_type_id = serializers.IntegerField(source='product_type.id')
    product_type_name = serializers.CharField(source='product_type.name')
    total_quantity = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    avg_unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    daily_capacity = serializers.IntegerField(source='product_type.daily_production_capacity')
    demand_vs_capacity = serializers.SerializerMethodField()

    def get_demand_vs_capacity(self, obj):
        cap = obj['product_type'].daily_production_capacity
        return round((obj['total_quantity'] / max(cap, 1)) * 100, 2)


class DashboardCustomerMetricsSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField(source='customer.id')
    customer_name = serializers.CharField(source='customer.name')
    total_orders = serializers.IntegerField()
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    avg_order_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    last_order_date = serializers.DateField()
    points = serializers.IntegerField()
    retention_rate = serializers.FloatField()  # Added
    is_vip = serializers.SerializerMethodField()

    def get_is_vip(self, obj):
        return obj['total_spent'] >= 5000


class DashboardMetricsSerializer(serializers.Serializer):
    total_orders = serializers.IntegerField()
    active_orders = serializers.IntegerField()
    completed_today = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    revenue_today = serializers.DecimalField(max_digits=14, decimal_places=2)
    avg_order_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    avg_design_time_days = serializers.FloatField()
    avg_delivery_time_days = serializers.FloatField()
    overdue_orders = serializers.IntegerField()
    urgent_orders = serializers.IntegerField()
    payment_collection_rate = serializers.FloatField()
    production_load_today = serializers.FloatField()
    top_product_type = serializers.CharField(allow_null=True)