from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Property, Review

class PropertySerializer(serializers.ModelSerializer):
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
            'pictures',
        )

    def create(self, validated_data):
        # Obtener el usuario actual como propietario
        owner = self.context['request'].user
        property_instance = Property.objects.create(owner=owner, **validated_data)
        return property_instance


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
