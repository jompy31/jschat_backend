from rest_framework import serializers
from .models import Product, Characteristic, SubProduct, Service, Combo, TeamMember, BusinessHour, Coupon
import json
import logging

# Configura el logger
logger = logging.getLogger(__name__)

class CharacteristicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Characteristic
        fields = ['id', 'name', 'description']

class ServiceSerializer(serializers.ModelSerializer):
    subproduct = serializers.PrimaryKeyRelatedField(
        queryset=SubProduct.objects.all(),
        required=True
    )

    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'price', 'subproduct', 'code', 'duration']

    def validate_subproduct(self, value):
        if not SubProduct.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("El subproducto especificado no existe.")
        return value

class TeamMemberSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = TeamMember
        fields = ['id', 'name', 'position', 'photo']

    def create(self, validated_data):
        photo = validated_data.pop('photo', None)
        instance = TeamMember.objects.create(**validated_data)
        if photo:
            instance.photo = photo
            instance.save()
        return instance

    def update(self, instance, validated_data):
        photo = validated_data.pop('photo', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if photo:
            if instance.photo:
                instance.photo.delete(save=False)
            instance.photo = photo
        instance.save()
        return instance

class BusinessHourSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessHour
        fields = ['id', 'day', 'start_time', 'end_time']

    def validate_day(self, value):
        valid_days = [choice[0] for choice in BusinessHour.DAY_CHOICES]
        if value.lower() not in valid_days:
            raise serializers.ValidationError(f"Invalid day: {value}. Valid days are {valid_days}")
        return value.lower()

class CouponSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Coupon
        fields = ['id', 'name', 'code', 'image', 'description', 'price', 'discount']

    def create(self, validated_data):
        image = validated_data.pop('image', None)
        instance = Coupon.objects.create(**validated_data)
        if image:
            instance.image = image
            instance.save()
        return instance

    def update(self, instance, validated_data):
        image = validated_data.pop('image', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if image:
            if instance.image:
                instance.image.delete(save=False)
            instance.image = image
        instance.save()
        return instance

class SubProductSerializer(serializers.ModelSerializer):
    products = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Product.objects.all(), 
        required=True
    )
    business_hours = BusinessHourSerializer(many=True, required=False)
    team_members = TeamMemberSerializer(many=True, required=False)
    coupons = CouponSerializer(many=True, required=False)
    services = ServiceSerializer(many=True, read_only=True)

    class Meta:
        model = SubProduct
        fields = [
            'id', 'name', 'phone', 'email', 'address', 'addressmap', 'image', 'url',
            'description', 'country', 'province', 'canton', 'distrito', 'constitucion',
            'contact_name', 'phone_number', 'comercial_activity', 'pay_method', 'logo',
            'file', 'products', 'product_names', 'subcategory', 'subsubcategory',
            'team_members', 'business_hours', 'coupons', 'certified', 'services','point_of_sale'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Exclude relations for GET requests if specified in context
        if self.context.get('exclude_relations', False):
            self.fields.pop('team_members', None)
            self.fields.pop('business_hours', None)
            self.fields.pop('coupons', None)
            
    def to_internal_value(self, data):
        logger.debug(f"to_internal_value: Original data: {data}")

        # Create a mutable copy of data
        processed_data = {}
        mutable_data = data.dict()
        logger.debug(f"to_internal_value: Mutable data: {mutable_data}")

        # Extract files from request.FILES
        files = self.context['request'].FILES
        logger.debug(f"to_internal_value: Files received: {files}")

        # Procesar business_hours
        business_hours_data = []
        for key in list(mutable_data.keys()):
            if key.startswith('business_hours['):
                parts = key.split('[')
                index = int(parts[1].split(']')[0])
                field = parts[2].split(']')[0]
                while len(business_hours_data) <= index:
                    business_hours_data.append({})
                value = mutable_data[key]
                business_hours_data[index][field] = value
                del mutable_data[key]
        
        valid_business_hours = [
            bh for bh in business_hours_data
            if bh.get('day') and bh.get('start_time') and bh.get('end_time')
        ]
        if valid_business_hours:
            business_hour_serializer = BusinessHourSerializer(data=valid_business_hours, many=True)
            business_hour_serializer.is_valid(raise_exception=True)
            processed_data['business_hours'] = business_hour_serializer.validated_data
            logger.debug(f"to_internal_value: Processed business hours: {valid_business_hours}")

        # Procesar team_members
        team_members_data = []
        for key in list(mutable_data.keys()):
            if key.startswith('team_members[') and not key.endswith('[photo]'):
                parts = key.split('[')
                index = int(parts[1].split(']')[0])
                field = parts[2].split(']')[0]
                while len(team_members_data) <= index:
                    team_members_data.append({})
                value = mutable_data[key]
                team_members_data[index][field] = value
                del mutable_data[key]
        
        for index, tm in enumerate(team_members_data):
            photo_key = f'team_members[{index}][photo]'
            if photo_key in files:
                tm['photo'] = files[photo_key]
        
        valid_team_members = [
            tm for tm in team_members_data
            if tm.get('name') and tm.get('position')
        ]
        if valid_team_members:
            team_member_serializer = TeamMemberSerializer(data=valid_team_members, many=True)
            team_member_serializer.is_valid(raise_exception=True)
            processed_data['team_members'] = team_member_serializer.validated_data
            logger.debug(f"to_internal_value: Processed team members: {valid_team_members}")

        # Procesar coupons
        coupons_data = []
        for key in list(mutable_data.keys()):
            if key.startswith('coupons['):
                parts = key.split('[')
                index = int(parts[1].split(']')[0])
                field = parts[2].split(']')[0]
                while len(coupons_data) <= index:
                    coupons_data.append({})
                value = mutable_data[key]
                coupons_data[index][field] = value
                del mutable_data[key]
        
        for index, coupon in enumerate(coupons_data):
            image_key = f'coupons[{index}][image]'
            if image_key in files:
                coupon['image'] = files[image_key]
        
        valid_coupons = [
            coupon for coupon in coupons_data
            if coupon.get('name') and coupon.get('code') and coupon.get('description')
        ]
        if valid_coupons:
            coupon_serializer = CouponSerializer(data=valid_coupons, many=True)
            coupon_serializer.is_valid(raise_exception=True)
            processed_data['coupons'] = coupon_serializer.validated_data
            logger.debug(f"to_internal_value: Processed coupons: {valid_coupons}")

        # Procesar productos
        products_data = []
        for key in list(mutable_data.keys()):
            if key.startswith('products['):
                value = mutable_data[key]
                try:
                    product_id = int(value)
                    products_data.append(product_id)
                except (ValueError, TypeError) as e:
                    logger.warning(f"to_internal_value: Invalid product ID: {value}, error: {e}, skipping")
                    continue
                del mutable_data[key]

        # Handle products as a single list (alternative format)
        if 'products' in mutable_data:
            products = mutable_data['products']
            logger.debug(f"to_internal_value: Processing products field: {products}")
            if isinstance(products, str):
                try:
                    products = json.loads(products)
                except (ValueError, TypeError, json.JSONDecodeError) as e:
                    logger.warning(f"to_internal_value: Invalid product IDs format: {products}, error: {e}, skipping")
                    del mutable_data['products']
                    products = []
            elif not isinstance(products, list):
                logger.warning(f"to_internal_value: Products must be a list of IDs, got {products}, skipping")
                del mutable_data['products']
                products = []
            
            for value in products:
                try:
                    product_id = int(value)
                    products_data.append(product_id)
                except (ValueError, TypeError) as e:
                    logger.warning(f"to_internal_value: Invalid product ID in list: {value}, error: {e}, skipping")
                    continue
            del mutable_data['products']
        
        logger.debug(f"to_internal_value: Collected product IDs: {products_data}")
        if products_data:
            existing_products = Product.objects.filter(id__in=products_data).values_list('id', flat=True)
            logger.debug(f"to_internal_value: Existing product IDs: {existing_products}")
            missing_products = set(products_data) - set(existing_products)
            if missing_products:
                logger.error(f"to_internal_value: Products with IDs {missing_products} do not exist")
                raise serializers.ValidationError({
                    'products': f"Products with IDs {missing_products} do not exist."
                })
            # No asignamos processed_data['products'] aquí; dejamos que el serializer base lo maneje
            mutable_data['products'] = products_data  # Pasamos los IDs directamente al serializer
            logger.debug(f"to_internal_value: Assigned products to mutable_data: {products_data}")
        else:
            logger.error("to_internal_value: No valid product IDs provided")
            raise serializers.ValidationError({
                'products': "At least one valid product ID is required."
            })

        # Handle SubProduct image, logo, and file fields
        if 'image' in files:
            mutable_data['image'] = files['image']
        if 'logo' in files:
            mutable_data['logo'] = files['logo']
        if 'file' in files:
            mutable_data['file'] = files['file']

        if 'image_url' in mutable_data and 'image' not in files:
            del mutable_data['image_url']
        if 'logo_url' in mutable_data and 'logo' not in files:
            del mutable_data['logo_url']
        if 'file_url' in mutable_data and 'file' not in files:
            del mutable_data['file_url']

        if 'certified' in mutable_data and isinstance(mutable_data['certified'], str):
            mutable_data['certified'] = mutable_data['certified'].lower() == 'true'
        if 'point_of_sale' in mutable_data and isinstance(mutable_data['point_of_sale'], str):
            mutable_data['point_of_sale'] = mutable_data['point_of_sale'].lower() == 'true'

        logger.debug(f"to_internal_value: Mutable data before super().to_internal_value: {mutable_data}")
        internal_data = super().to_internal_value(mutable_data)
        internal_data.update(processed_data)
        logger.debug(f"to_internal_value: Final internal data: {internal_data}")

        return internal_data

    def create(self, validated_data):
        logger.debug(f"create: Validated data: {validated_data}")

        products_data = validated_data.pop('products')
        business_hours_data = validated_data.pop('business_hours', [])
        team_members_data = validated_data.pop('team_members', [])
        coupons_data = validated_data.pop('coupons', [])

        subproduct = SubProduct.objects.create(**validated_data)
        logger.debug(f"create: Created SubProduct with ID: {subproduct.id}")

        if products_data:
            subproduct.products.set(products_data)
            logger.debug(f"create: Assigned products: {products_data}")

        for bh_data in business_hours_data:
            business_hour = BusinessHour.objects.create(**bh_data)
            subproduct.business_hours.add(business_hour)
            logger.debug(f"create: Created BusinessHour: {business_hour}")

        for tm_data in team_members_data:
            photo = tm_data.pop('photo', None)
            team_member = TeamMember.objects.create(**tm_data)
            if photo:
                team_member.photo = photo
                team_member.save()
            subproduct.team_members.add(team_member)
            logger.debug(f"create: Created TeamMember: {team_member}")

        for coupon_data in coupons_data:
            image = coupon_data.pop('image', None)
            coupon = Coupon.objects.create(**coupon_data)
            if image:
                coupon.image = image
                coupon.save()
            subproduct.coupons.add(coupon)
            logger.debug(f"create: Created Coupon: {coupon}")

        return subproduct

    def update(self, instance, validated_data):
        logger.debug(f"update: Validated data: {validated_data}")

        products_data = validated_data.pop('products', None)
        business_hours_data = validated_data.pop('business_hours', None)
        team_members_data = validated_data.pop('team_members', None)
        coupons_data = validated_data.pop('coupons', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if 'image' not in validated_data and instance.image:
            validated_data['image'] = instance.image
        if 'logo' not in validated_data and instance.logo:
            validated_data['logo'] = instance.logo
        if 'file' not in validated_data and instance.file:
            validated_data['file'] = instance.file

        instance.save()
        logger.debug(f"update: Updated SubProduct with ID: {instance.id}")

        if products_data is not None:
            instance.products.set(products_data)
            logger.debug(f"update: Updated products: {products_data}")

        if business_hours_data is not None:
            instance.business_hours.clear()
            for bh_data in business_hours_data:
                business_hour = BusinessHour.objects.create(**bh_data)
                instance.business_hours.add(business_hour)
                logger.debug(f"update: Created BusinessHour: {business_hour}")

        if team_members_data is not None:
            existing_team_members = {(tm.name, tm.position): tm for tm in instance.team_members.all()}
            new_team_members = []

            for tm_data in team_members_data:
                name = tm_data.get('name')
                position = tm_data.get('position')
                photo = tm_data.pop('photo', None)

                key = (name, position)
                if key in existing_team_members:
                    team_member = existing_team_members[key]
                    for attr, value in tm_data.items():
                        setattr(team_member, attr, value)
                    if photo:
                        if team_member.photo:
                            team_member.photo.delete(save=False)
                        team_member.photo = photo
                    team_member.save()
                else:
                    team_member = TeamMember.objects.create(**tm_data)
                    if photo:
                        team_member.photo = photo
                        team_member.save()
                    logger.debug(f"update: Created TeamMember: {team_member}")
                
                new_team_members.append(team_member)

            instance.team_members.set(new_team_members)

        if coupons_data is not None:
            existing_coupons = {coupon.code: coupon for coupon in instance.coupons.all()}
            new_coupons = []

            for coupon_data in coupons_data:
                code = coupon_data.get('code')
                image = coupon_data.pop('image', None)

                if code in existing_coupons:
                    coupon = existing_coupons[code]
                    for attr, value in coupon_data.items():
                        setattr(coupon, attr, value)
                    if image:
                        if coupon.image:
                            coupon.image.delete(save=False)
                        coupon.image = image
                    coupon.save()
                else:
                    coupon = Coupon.objects.create(**coupon_data)
                    if image:
                        coupon.image = image
                        coupon.save()
                    logger.debug(f"update: Created Coupon: {coupon}")
                
                new_coupons.append(coupon)

            instance.coupons.set(new_coupons)

        return instance

class ComboSerializer(serializers.ModelSerializer):
    services = ServiceSerializer(many=True, read_only=True)
    subproduct = serializers.PrimaryKeyRelatedField(
        queryset=SubProduct.objects.all(),
        required=True
    )

    class Meta:
        model = Combo
        fields = ['id', 'code', 'name', 'description', 'price', 'services', 'subproduct']

    def validate(self, attrs):
        subproduct = attrs.get('subproduct')
        if not SubProduct.objects.filter(id=subproduct.id).exists():
            raise serializers.ValidationError({"subproduct": "El subproducto especificado no existe."})

        if self.context.get('request').method == 'POST':
            selected_service_ids = self.context.get('request').data.get('selectedServiceIds', [])
            if selected_service_ids:
                invalid_services = Service.objects.filter(id__in=selected_service_ids).exclude(subproduct=subproduct)
                if invalid_services.exists():
                    raise serializers.ValidationError({
                        "selectedServiceIds": "Uno o más servicios no están asociados al subproducto especificado."
                    })
        return attrs

class ProductSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    characteristics = CharacteristicSerializer(many=True, read_only=True)
    subproducts = SubProductSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'file', 'file1', 'user', 'created_at', 'name', 'name_url',
            'description', 'characteristics', 'subproducts'
        ]
        extra_kwargs = {
            'file': {'required': False},
            'file1': {'required': False},
        }

    def create(self, validated_data):
        product = Product.objects.create(**validated_data)
        return product

    def update(self, instance, validated_data):
        file = validated_data.pop('file', None)
        file1 = validated_data.pop('file1', None)

        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.name_url = validated_data.get('name_url', instance.name_url)

        if file is not None:
            instance.file = file
        if file1 is not None:
            instance.file1 = file1

        instance.save()
        return instance