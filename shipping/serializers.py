from rest_framework import serializers
from .models import Product, Review, Order, OrderItem, ShippingAddress, ProductImage, Form, FormField, FormResponse


# Serializador para los campos del formulario
class FormFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormField
        fields = '__all__'

# Serializador para las respuestas del formulario
class FormResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormResponse
        fields = '__all__'

    def create(self, validated_data):
        # Obtener el ID del campo del formulario
        form_field_id = validated_data.pop('form_field')  # Obtener el ID
        form_field_instance = FormField.objects.get(_id=form_field_id)  # Obtener la instancia
        validated_data['form_field'] = form_field_instance  # Asignar la instancia
        
        # Verificar si ya existe una respuesta con los mismos datos
        existing_response = FormResponse.objects.filter(
            form_field=form_field_instance,
            **{k: validated_data[k] for k in validated_data if k != 'form_field'}
        ).first()

        if existing_response:
            # Si ya existe, retorna la instancia existente en lugar de crear una nueva
            return existing_response

        # Si no existe, procedemos a crear una nueva
        return super().create(validated_data)

# Serializador para el formulario, que incluye los campos y las respuestas
class FormSerializer(serializers.ModelSerializer):
    fields = FormFieldSerializer(many=True, required=False)  # Cambia required a False
    responses = FormResponseSerializer(many=True, read_only=True)
    product = serializers.PrimaryKeyRelatedField(many=True, queryset=Product.objects.all(), required=False)  # Cambia required a False
    

    class Meta:
        model = Form
        fields = '__all__'

    def create(self, validated_data):
        fields_data = validated_data.pop('fields', [])
        product_data = validated_data.pop('product', [])  # Obtener los productos para asociar
        form = Form.objects.create(**validated_data)

        # Asociar productos
        form.product.set(product_data)

        for field_data in fields_data:
            FormField.objects.create(form=form, **field_data)

        return form


    # Actualizar el formulario y sus campos
    def update(self, instance, validated_data):
        fields_data = validated_data.pop('fields', None)
        
        # Actualiza el formulario
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.save()

        # Si se proporcionan campos, actualízalos
        if fields_data:
            instance.fields.all().delete()  # Elimina los campos existentes
            for field_data in fields_data:
                FormField.objects.create(form=instance, **field_data)

        return instance

class ProductSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Product
        fields = '__all__'

    def update(self, instance, validated_data):
        # Eliminar el campo 'image' si no se incluye en los datos validados
        validated_data.pop('image', None)
        return super().update(instance, validated_data)


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = '__all__'

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = '__all__'

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'

class ShippingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingAddress
        fields = '__all__'

class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)
    shipping_address = ShippingAddressSerializer(read_only=True)

    class Meta:
        model = Order
        fields = '__all__'

class OrderItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'

