from rest_framework import serializers
from .models import File, NewsPost, Service, Distributor, Design

class FileSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = File
        fields = ['id', 'file', 'user', 'created_at', 'name']

class NewsPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsPost
        fields = ['id', 'title', 'category','subcategory', 'subsubcategory', 'country','province','description', 'content_type', 'content', 'datetime', 'phone_number', 'whatsapp', 'url']

    def update(self, instance, validated_data):
        # Verificar si hay un nuevo archivo
        content = validated_data.get('content', None)
        if content is None:
            # Si no hay nuevo contenido, usar el existente
            validated_data['content'] = instance.content

        return super().update(instance, validated_data)
    
class DistributorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Distributor
        fields = '__all__'

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'price']
class DesignSerializer(serializers.ModelSerializer):
    created_by = serializers.ReadOnlyField(source='created_by.username')

    class Meta:
        model = Design
        fields = ['id', 'name', 'customer', 'context', 'created_by', 'created_at', 'url', 'image']
