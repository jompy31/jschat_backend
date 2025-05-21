from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from django.db import transaction
from django.core.cache import cache
from django.core.files.storage import default_storage
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.db.models import Prefetch
import logging
from datetime import datetime
import os
from .models import Product, Characteristic, SubProduct, Service, Combo, TeamMember, BusinessHour, Coupon
from .serializers import (
    ProductSerializer, CharacteristicSerializer, SubProductSerializer,
    ServiceSerializer, ComboSerializer, TeamMemberSerializer,
    BusinessHourSerializer, CouponSerializer
)

# Configura el logger
logger = logging.getLogger(__name__)

class SubProductByEmailView(APIView):
    def get(self, request, email, format=None):
        logger.info(f"Fetching subproduct with email: {email}")
        try:
            subproduct = SubProduct.objects.prefetch_related(
                Prefetch('service_set', queryset=Service.objects.all()),
                Prefetch('team_members', queryset=TeamMember.objects.all()),
                Prefetch('coupons', queryset=Coupon.objects.all()),
                Prefetch('business_hours', queryset=BusinessHour.objects.all())
            ).get(email__iexact=email)

            service_ids = subproduct.service_set.values_list('id', flat=True)
            combos = Combo.objects.filter(subproduct=subproduct).prefetch_related('services')

            # Pasar el contexto de la solicitud a los serializadores
            serializer_context = {'request': request}

            subproduct_serializer = SubProductSerializer(subproduct, context=serializer_context)
            services_serializer = ServiceSerializer(subproduct.service_set.all(), many=True, context=serializer_context)
            combos_serializer = ComboSerializer(combos, many=True, context=serializer_context)
            team_members_serializer = TeamMemberSerializer(subproduct.team_members.all(), many=True, context=serializer_context)
            coupons_serializer = CouponSerializer(subproduct.coupons.all(), many=True, context=serializer_context)
            business_hours_serializer = BusinessHourSerializer(subproduct.business_hours.all(), many=True, context=serializer_context)

            response_data = {
                'subproduct': subproduct_serializer.data,
                'services': services_serializer.data,
                'combos': combos_serializer.data,
                'team_members': team_members_serializer.data,
                'coupons': coupons_serializer.data,
                'business_hours': business_hours_serializer.data
            }

            logger.debug(f"Successfully fetched subproduct: {subproduct.name}")
            return Response(response_data, status=status.HTTP_200_OK)
        except SubProduct.DoesNotExist:
            logger.warning(f"Subproduct with email {email} not found")
            return Response({'error': 'Subproduct not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error fetching subproduct with email {email}: {str(e)}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TeamMemberListCreateView(generics.ListCreateAPIView):
    serializer_class = TeamMemberSerializer

    def get_queryset(self):
        subproduct_id = self.kwargs['subproduct_id']
        queryset = TeamMember.objects.filter(subproducts=subproduct_id)
        return queryset

    def list(self, request, *args, **kwargs):
        cache_key = f'teammembers_subproduct_{self.kwargs["subproduct_id"]}'
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        queryset = self.filter_queryset(self.get_queryset())
        serialized_data = TeamMemberSerializer(queryset, many=True).data
        cache.set(cache_key, serialized_data, timeout=3600)
        return Response(serialized_data)

    def perform_create(self, serializer):
        subproduct_id = self.kwargs['subproduct_id']
        try:
            subproduct = SubProduct.objects.get(id=subproduct_id)
            instance = serializer.save()
            instance.subproducts.add(subproduct)
            cache.delete(f'teammembers_subproduct_{subproduct_id}')
        except SubProduct.DoesNotExist:
            return Response(
                {"error": "SubProduct not found"},
                status=status.HTTP_404_NOT_FOUND
            )

class TeamMemberRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer

    def perform_destroy(self, instance):
        subproduct_id = instance.subproducts.first().id
        super().perform_destroy(instance)
        cache.delete(f'teammembers_subproduct_{subproduct_id}')

class BusinessHourListCreateView(generics.ListCreateAPIView):
    serializer_class = BusinessHourSerializer

    def get_queryset(self):
        subproduct_id = self.kwargs['subproduct_id']
        cache_key = f'businesshours_subproduct_{subproduct_id}'
        cached_data = cache.get(cache_key)
        if cached_data:
            return BusinessHour.objects.filter(id__in=[item['id'] for item in cached_data])
        queryset = BusinessHour.objects.filter(subproducts__id=subproduct_id)
        serialized_data = BusinessHourSerializer(queryset, many=True).data
        cache.set(cache_key, serialized_data, timeout=3600)
        return queryset

    def perform_create(self, serializer):
        subproduct_id = self.kwargs['subproduct_id']
        subproduct = SubProduct.objects.get(pk=subproduct_id)
        serializer.save(subproduct=subproduct)
        cache.delete(f'businesshours_subproduct_{subproduct_id}')

class BusinessHourRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BusinessHour.objects.all()
    serializer_class = BusinessHourSerializer

    def perform_destroy(self, instance):
        subproduct_id = instance.subproducts.first().id
        super().perform_destroy(instance)
        cache.delete(f'businesshours_subproduct_{subproduct_id}')

class CouponListCreateView(generics.ListCreateAPIView):
    serializer_class = CouponSerializer

    def get_queryset(self):
        subproduct_id = self.kwargs['subproduct_id']
        queryset = Coupon.objects.filter(subproducts=subproduct_id)
        return queryset

    def list(self, request, *args, **kwargs):
        cache_key = f'coupons_subproduct_{self.kwargs["subproduct_id"]}'
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        queryset = self.filter_queryset(self.get_queryset())
        serialized_data = CouponSerializer(queryset, many=True).data
        cache.set(cache_key, serialized_data, timeout=3600)
        return Response(serialized_data)

    def perform_create(self, serializer):
        subproduct_id = self.kwargs['subproduct_id']
        try:
            subproduct = SubProduct.objects.get(id=subproduct_id)
            instance = serializer.save()
            instance.subproducts.add(subproduct)
            cache.delete(f'coupons_subproduct_{subproduct_id}')
        except SubProduct.DoesNotExist:
            return Response(
                {"error": "SubProduct not found"},
                status=status.HTTP_404_NOT_FOUND
            )

class CouponRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer

    def perform_destroy(self, instance):
        subproduct_id = instance.subproducts.first().id
        super().perform_destroy(instance)
        cache.delete(f'coupons_subproduct_{subproduct_id}')


class PointOfSaleSubProductList(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = SubProductSerializer
    
    def get_queryset(self):
        cache_key = 'subproducts_point_of_sale'
        cached_data = cache.get(cache_key)
        if cached_data:
            return SubProduct.objects.filter(id__in=[item['id'] for item in cached_data]).order_by('name')
        # Only prefetch products, exclude business_hours, team_members, coupons
        queryset = SubProduct.objects.filter(point_of_sale=True).prefetch_related('products').order_by('name')
        serialized_data = SubProductSerializer(
            queryset, 
            many=True, 
            context={'request': self.request, 'exclude_relations': True}
        ).data
        cache.set(cache_key, serialized_data, timeout=3600)
        return queryset

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            logger.debug("Successfully fetched subproducts with point_of_sale=True")
            return Response(serializer.data, status=200)
        except Exception as e:
            logger.error(f"Error fetching subproducts with point_of_sale=True: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=500)

class SubProductListCreate(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = SubProductSerializer
    
    def get_queryset(self):
        cache_key = 'subproducts_all'
        cached_data = cache.get(cache_key)
        if cached_data:
            return SubProduct.objects.filter(id__in=[item['id'] for item in cached_data]).order_by('name')
        # Only prefetch products, exclude business_hours, team_members, coupons
        queryset = SubProduct.objects.all().prefetch_related('products').order_by('name')
        serialized_data = SubProductSerializer(
            queryset, 
            many=True, 
            context={'request': self.request, 'exclude_relations': True}
        ).data
        cache.set(cache_key, serialized_data, timeout=3600)
        return queryset

    def post(self, request, *args, **kwargs):
        print("=== Received POST request to create SubProduct ===")
        print("Raw request data1:", request.data)
        print("Raw request data:", dict(request.data))
        print("Files received:", request.FILES)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("Validation errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        print("Validated data:", serializer.validated_data)

        try:
            with transaction.atomic():
                # Crear el subproducto usando el serializador
                subproduct = serializer.save()
                print(f"SubProduct created with ID: {subproduct.id}")
                print(f"Associated products: {subproduct.products.all()}")
                print(f"Associated business hours: {subproduct.business_hours.all()}")
                print(f"Associated team members: {subproduct.team_members.all()}")
                print(f"Associated coupons: {subproduct.coupons.all()}")

                # Invalidar caché
                cache.delete('subproducts_all')
                print("Cache invalidated for 'subproducts_all'")

            return Response(
                {
                    "message": "SubProduct created successfully",
                    "subproduct_id": subproduct.id,
                    "data": SubProductSerializer(subproduct).data
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            print(f"Error creating SubProduct: {str(e)}")
            logger.error(f"Error in SubProductListCreate.post: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SubProductRetrieveUpdate(generics.RetrieveUpdateAPIView):
    queryset = SubProduct.objects.all().prefetch_related(
        'products', 'business_hours', 'team_members', 'coupons'
    )
    serializer_class = SubProductSerializer

    def get_object(self):
        pk = self.kwargs['pk']
        cache_key = f'subproduct_{pk}'
        cached_data = cache.get(cache_key)
        if cached_data:
            return SubProduct.objects.get(id=cached_data['id'])
        obj = super().get_object()
        serialized_data = SubProductSerializer(obj).data
        cache.set(cache_key, serialized_data, timeout=3600)
        return obj

    def update(self, request, *args, **kwargs):
        print("=== Received PUT/PATCH request to update SubProduct ===")
        print("Raw request data:", dict(request.data))
        print("Files received:", request.FILES)

        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            print("Validation errors:", serializer._errors if hasattr(serializer, '_errors') else str(e))
            return Response({"error": str(e), "details": serializer._errors if hasattr(serializer, '_errors') else {}}, status=status.HTTP_400_BAD_REQUEST)

        print("Validated data:", serializer.validated_data)

        try:
            with transaction.atomic():
                # Actualizar el subproducto usando el serializador
                subproduct = serializer.save()
                print(f"SubProduct updated with ID: {subproduct.id}")
                print(f"Associated products: {subproduct.products.all()}")
                print(f"Associated business hours: {subproduct.business_hours.all()}")
                print(f"Associated team members: {subproduct.team_members.all()}")
                print(f"Associated coupons: {subproduct.coupons.all()}")

                # Invalidar caché
                cache.delete('subproducts_all')
                cache.delete(f'subproduct_{subproduct.id}')
                print(f"Cache invalidated for 'subproducts_all' and 'subproduct_{subproduct.id}'")

            return Response(
                {
                    "message": "SubProduct updated successfully",
                    "subproduct_id": subproduct.id,
                    "data": SubProductSerializer(subproduct).data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            print(f"Error updating SubProduct: {str(e)}")
            logger.error(f"Error in SubProductRetrieveUpdate.update: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SubProductDestroy(generics.DestroyAPIView):
    queryset = SubProduct.objects.all()
    serializer_class = SubProductSerializer

    def perform_destroy(self, instance):
        product_names = instance.product_names.split(',') if instance.product_names else []
        if "nombre_producto_a_eliminar" in product_names:
            product_names.remove("nombre_producto_a_eliminar")
            instance.product_names = ','.join(product_names)
            instance.save()
        instance.delete()
        cache.delete('subproducts_all')
        cache.delete(f'subproduct_{instance.id}')

class SubProductServicesView(generics.ListCreateAPIView):
    serializer_class = ServiceSerializer

    def get_queryset(self):
        subproduct_id = self.kwargs['subproduct_id']
        cache_key = f'services_subproduct_{subproduct_id}'
        cached_data = cache.get(cache_key)
        if cached_data:
            return Service.objects.filter(id__in=[item['id'] for item in cached_data])
        queryset = Service.objects.filter(subproduct_id=subproduct_id)
        serialized_data = ServiceSerializer(queryset, many=True).data
        cache.set(cache_key, serialized_data, timeout=3600)
        return queryset

    def perform_create(self, serializer):
        subproduct_id = self.kwargs['subproduct_id']
        try:
            subproduct = SubProduct.objects.get(id=subproduct_id)
            # Asignar el subproducto al servicio
            serializer.save(subproduct=subproduct)
            cache.delete(f'services_subproduct_{subproduct_id}')
        except SubProduct.DoesNotExist:
            return Response(
                {"error": "SubProduct not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    def put(self, request, subproduct_id, *args, **kwargs):
        service_id = request.data.get('service_id')
        try:
            service = Service.objects.get(id=service_id, subproduct_id=subproduct_id)
        except Service.DoesNotExist:
            return Response({"message": "Service not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ServiceSerializer(service, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            cache.delete(f'services_subproduct_{subproduct_id}')
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ServiceDeleteView(APIView):
    def delete(self, request, subproducts_id, service_id):
        try:
            service = Service.objects.get(id=service_id, subproduct_id=subproducts_id)
            service.delete()
            cache.delete(f'services_subproduct_{subproducts_id}')
            return Response({"message": "Service deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Service.DoesNotExist:
            return Response({"message": "Service not found"}, status=status.HTTP_404_NOT_FOUND)

class SubProductServicesListAll(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        cache_key = 'services_all'
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)
        services = Service.objects.all().select_related('subproduct')
        serialized_data = ServiceSerializer(services, many=True).data
        cache.set(cache_key, serialized_data, timeout=3600)
        return Response(serialized_data, status=status.HTTP_200_OK)

class ComboListCreate(generics.ListCreateAPIView):
    serializer_class = ComboSerializer
    queryset = Combo.objects.all().prefetch_related('services')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        name = serializer.validated_data.get('name')
        description = serializer.validated_data.get('description')
        price = serializer.validated_data.get('price')
        subproduct = serializer.validated_data.get('subproduct')
        selected_service_ids = request.data.get('selectedServiceIds', [])

        if not all([name, description, price, subproduct]):
            return Response({"error": "All fields (name, description, price, subproduct) are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            price = float(price)
        except ValueError:
            return Response({"error": "Price must be a valid number"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Crear el combo con el subproducto
            combo = Combo.objects.create(
                name=name,
                description=description,
                price=price,
                subproduct=subproduct
            )
            for service_id in selected_service_ids:
                try:
                    service = Service.objects.get(id=service_id, subproduct=subproduct)
                    combo.services.add(service)
                except Service.DoesNotExist:
                    return Response({"error": f"Service with ID {service_id} not found or not associated with the specified subproduct"}, status=status.HTTP_400_BAD_REQUEST)

        cache.delete('combos_all')
        return Response(ComboSerializer(combo).data, status=status.HTTP_201_CREATED)

class ComboRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Combo.objects.all().prefetch_related('services')
    serializer_class = ComboSerializer

    def perform_destroy(self, instance):
        instance.delete()
        cache.delete('combos_all')

class ProductListCreate(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    queryset = Product.objects.all().prefetch_related('characteristics', 'subproducts')

    def perform_create(self, serializer):
        characteristics_ids = self.request.data.getlist('characteristics', [])
        product = serializer.save(user=self.request.user)
        if characteristics_ids:
            for char_id in characteristics_ids:
                try:
                    char = Characteristic.objects.get(pk=char_id)
                    product.characteristics.add(char)
                except Characteristic.DoesNotExist:
                    pass
        cache.delete('products_all')

class ProductRetrieveUpdate(generics.RetrieveUpdateAPIView):
    queryset = Product.objects.all().prefetch_related('characteristics', 'subproducts')
    serializer_class = ProductSerializer

    def get_object(self):
        pk = self.kwargs['pk']
        cache_key = f'product_{pk}'
        cached_data = cache.get(cache_key)
        if cached_data:
            return Product.objects.get(id=cached_data['id'])
        obj = super().get_object()
        serialized_data = ProductSerializer(obj).data
        cache.set(cache_key, serialized_data, timeout=3600)
        return obj

class ProductDestroy(generics.DestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def perform_destroy(self, instance):
        instance.delete()
        cache.delete('products_all')
        cache.delete(f'product_{instance.id}')

class CharacteristicListCreate(generics.ListCreateAPIView):
    serializer_class = CharacteristicSerializer
    queryset = Characteristic.objects.all()

class CharacteristicRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Characteristic.objects.all()
    serializer_class = CharacteristicSerializer

class CharacteristicDestroy(generics.DestroyAPIView):
    queryset = Characteristic.objects.all()
    serializer_class = CharacteristicSerializer