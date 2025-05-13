from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Property, PropertyImage, Amenity, Booking, Payment, Review

class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ('id', 'name')  # Incluir el ID y nombre de la amenidad

class PropertyImageSerializer(serializers.ModelSerializer):
    property_id = serializers.IntegerField(source='property.id')  # Obtener el ID de la propiedad asociada

    class Meta:
        model = PropertyImage
        fields = ('image', 'property_id') 

class PropertySerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True
    )
    amenities = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True
    )  # Ajustar amenities para recibir una lista de IDs.

    owner = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)

    class Meta:
        model = Property
        fields = (
            'id',
            'owner',
            'title',
            'description',
            'location',
            'country',
            'province',
            'canton',
            'rating',
            'property_type',
            'bedrooms',
            'bathrooms',
            'price_per_night',
            'availability',
            'images',
            'amenities',
        )

    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        amenities_data = validated_data.pop('amenities', [])  # Procesar amenidades como lista de IDs.

        # Obtener el usuario actual como propietario
        owner = self.context['request'].user

        # Crear la propiedad
        property_instance = Property.objects.create(owner=owner, **validated_data)

        # Guardar las imágenes
        for image in images_data:
            PropertyImage.objects.create(property=property_instance, image=image)

        # Asociar las amenidades
        if amenities_data:
            property_instance.amenities.set(amenities_data)  # Relacionar amenidades.

        return property_instance

class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = (
            'id',
            'guest',
            'property',
            'check_in',
            'check_out',
            'total_price',
            'status',
        )

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            'id',
            'booking',
            'user',
            'amount',
            'payment_method',
            'payment_status',
        )

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = (
            'id',
            'user',
            'property',
            'rating',
            'comment',
            'createdAt',
        )
