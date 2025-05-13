from rest_framework import serializers
from .models import Product, Characteristic, SubProduct, Service, Combo, TeamMember, BusinessHour, Coupon

class CharacteristicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Characteristic
        fields = ['id', 'name', 'description']

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'price', 'subproduct', 'code', 'duration']

class TeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMember
        fields = '__all__'

class BusinessHourSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessHour
        fields = '__all__' 

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__' 
        
class SubProductSerializer(serializers.ModelSerializer):
    teammembers = TeamMemberSerializer(many=True, read_only=True)
    businesshours = BusinessHourSerializer(many=True, read_only=True)
    coupons = CouponSerializer(many=True, read_only=True)
    class Meta:
        model = SubProduct
        fields = '__all__'
        
    
    def add_product_name(self, subproduct_instance, product_name):
        if not subproduct_instance.product_names:
            subproduct_instance.product_names = product_name
        else:
            product_names_list = subproduct_instance.product_names.split(',')
            if product_name not in product_names_list:
                product_names_list.append(product_name)
                subproduct_instance.product_names = ','.join(product_names_list)

    def remove_product_name(self, subproduct_instance, product_name):
        if subproduct_instance.product_names:
            product_names_list = subproduct_instance.product_names.split(',')
            if product_name in product_names_list:
                product_names_list.remove(product_name)
                subproduct_instance.product_names = ','.join(product_names_list)

class ComboSerializer(serializers.ModelSerializer):
    services = ServiceSerializer(many=True, read_only=True)

    class Meta:
        model = Combo
        fields = ['id', 'code','name', 'description', 'price', 'services']

class ProductSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    characteristics = CharacteristicSerializer(many=True, required=False)
    subproducts = SubProductSerializer(many=True, read_only=True)
    combos = ComboSerializer(many=True, read_only=True)  # Add the ComboSerializer for nested combos
    
    class Meta:
        model = Product
        fields = ['id', 'file', 'file1', 'user', 'created_at', 'name', 'name_url', 'description', 'characteristics', 'subproducts', 'combos']
        extra_kwargs = {
            'file': {'required': False},
            'file1': {'required': False},
        }

    def create(self, validated_data):
        characteristics_data = validated_data.pop('characteristics', [])
        subproducts_data = validated_data.pop('subproducts', [])
        combos_data = validated_data.pop('combos', [])  # Handle nested combos

        product = Product.objects.create(**validated_data)

        for char_data in characteristics_data:
            char, _ = Characteristic.objects.get_or_create(**char_data)
            product.characteristics.add(char)

        for subproduct_data in subproducts_data:
            subproduct = SubProduct.objects.create(**subproduct_data)
            product.subproducts.add(subproduct)

        for combo_data in combos_data:
            combo = Combo.objects.create(**combo_data)
            product.combos.add(combo)

        return product

    def update(self, instance, validated_data):
        print("Datos recibidos para actualización:", validated_data)
        # Extraer datos de archivos
        file = validated_data.pop('file', None)
        file1 = validated_data.pop('file1', None)

        # Actualizar otros campos
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)

        # Si no se proporciona un nuevo archivo, conservar el existente
        if file is not None:
            instance.file = file
        if file1 is not None:
            instance.file1 = file1

        # Manejo de características
        characteristics_data = validated_data.pop('characteristics', None)
        print("Características recibidas:", characteristics_data)
        # Limpiar y añadir características solo si se proporcionan
        if characteristics_data is not None:
            instance.characteristics.clear()
            for char_data in characteristics_data:
                char, _ = Characteristic.objects.get_or_create(**char_data)
                instance.characteristics.add(char)

        # Guardar los cambios en el producto
        instance.save()
        return instance