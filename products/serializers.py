from rest_framework import serializers
from .models import ProductType, Characteristic, Product
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class CharacteristicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Characteristic
        fields = ['id', 'name', 'description']

class ProductTypeSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    created_by_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='created_by', write_only=True
    )
    
    class Meta:
        model = ProductType
        fields = [
            'id', 'name', 'description', 'base_price', 'delivery_time_days',
            'daily_production_capacity', 'created_by', 'created_by_id', 'created_at'
        ]

class ProductSerializer(serializers.ModelSerializer):
    product_type = ProductTypeSerializer(read_only=True)
    product_type_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductType.objects.all(), source='product_type', write_only=True
    )
    characteristics = CharacteristicSerializer(many=True, read_only=True)
    characteristic_ids = serializers.ListField(
        child=serializers.CharField(), write_only=True, source='characteristics'
    )
    created_by = UserSerializer(read_only=True)
    created_by_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='created_by', write_only=True
    )
    additional_price = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=False)
    
    class Meta:
        model = Product
        fields = [
            'id', 'product_type', 'product_type_id', 'name', 'description',
            'design_file', 'additional_price', 'characteristics', 'characteristic_ids',
            'created_by', 'created_by_id', 'created_at'
        ]
    
    def validate_characteristic_ids(self, value):
        """Custom validation for characteristic_ids to handle string inputs."""
        if not isinstance(value, list):
            raise serializers.ValidationError("characteristic_ids must be a list.")
        try:
            # Convert string IDs to integers
            char_ids = [int(item) for item in value]
        except (ValueError, TypeError):
            raise serializers.ValidationError("All characteristic_ids must be valid integers.")
        
        # Validate that each ID corresponds to an existing Characteristic
        for char_id in char_ids:
            if not Characteristic.objects.filter(id=char_id).exists():
                raise serializers.ValidationError(f"Characteristic with ID {char_id} does not exist.")
        return char_ids
    
    def validate_product_type_id(self, value):
        """Ensure product_type_id corresponds to an existing ProductType."""
        if not ProductType.objects.filter(id=value.id).exists():
            raise serializers.ValidationError(f"ProductType with ID {value.id} does not exist.")
        return value
    
    def validate_created_by_id(self, value):
        """Ensure created_by_id corresponds to an existing User."""
        if not User.objects.filter(id=value.id).exists():
            raise serializers.ValidationError(f"User with ID {value.id} does not exist.")
        return value
    
    def validate_design_file(self, value):
        """Validate design_file, allowing files, None, or empty string."""
        if value is None or value == '':
            return None
        if not hasattr(value, 'content_type'):
            logger.error(f"Invalid design_file: {value}")
            raise serializers.ValidationError("design_file must be a valid file or null.")
        # Optionally, restrict file types or sizes
        allowed_types = ['image/jpeg', 'image/png', 'application/pdf']
        max_size = 5 * 1024 * 1024  # 5MB
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(f"File type {value.content_type} not allowed. Allowed types: {allowed_types}")
        if value.size > max_size:
            raise serializers.ValidationError(f"File size exceeds {max_size / (1024 * 1024)}MB limit.")
        return value
    
    def validate(self, data):
        """Handle string inputs for product_type_id and created_by_id."""
        logger.debug(f"Datos recibidos en ProductSerializer.validate: {data}")
        try:
            # Convert string inputs to integers for product_type_id and created_by_id
            if isinstance(data.get('product_type'), str):
                try:
                    data['product_type'] = ProductType.objects.get(id=int(data['product_type']))
                except (ValueError, ProductType.DoesNotExist):
                    raise serializers.ValidationError("Invalid product_type_id.")
            if isinstance(data.get('created_by'), str):
                try:
                    data['created_by'] = User.objects.get(id=int(data['created_by']))
                except (ValueError, User.DoesNotExist):
                    raise serializers.ValidationError("Invalid created_by_id.")
            validated_data = super().validate(data)
            return validated_data
        except serializers.ValidationError as e:
            logger.error(f"Errores de validación en ProductSerializer: {e.detail}")
            raise
    
    def create(self, validated_data):
        logger.debug(f"Datos recibidos en ProductSerializer.create: {validated_data}")
        characteristics = validated_data.pop('characteristics', [])
        product = Product.objects.create(**validated_data)
        product.characteristics.set(characteristics)
        logger.info(f"Producto creado: {product}")
        return product
    
    def update(self, instance, validated_data):
        characteristics = validated_data.pop('characteristics', [])
        instance = super().update(instance, validated_data)
        instance.characteristics.set(characteristics)
        return instance