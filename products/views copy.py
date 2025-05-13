from rest_framework import generics
from .models import Product, Characteristic, SubProduct, Service, Combo, TeamMember, BusinessHour, Coupon
from .serializers import ProductSerializer, CharacteristicSerializer, SubProductSerializer, ServiceSerializer, ComboSerializer, TeamMemberSerializer,  BusinessHourSerializer, CouponSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
import logging
from django.db import transaction  
import json
from rest_framework.exceptions import ValidationError
import uuid

# Configura el logger
logger = logging.getLogger(__name__)


# TeamMember Views
class TeamMemberListCreateView(generics.ListCreateAPIView):
    serializer_class = TeamMemberSerializer

    def get_queryset(self):
        subproduct_id = self.kwargs['subproduct_id']
        # Filtra por el campo 'subproducts' en lugar de 'subproduct_id'
        return TeamMember.objects.filter(subproducts__id=subproduct_id)

    def perform_create(self, serializer):
        subproduct_id = self.kwargs['subproduct_id']
        subproduct = SubProduct.objects.get(pk=subproduct_id)
        serializer.save(subproduct=subproduct)

class TeamMemberRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer


# BusinessHour Views
class BusinessHourListCreateView(generics.ListCreateAPIView):
    serializer_class = BusinessHourSerializer

    def get_queryset(self):
        subproduct_id = self.kwargs['subproduct_id']
        return BusinessHour.objects.filter(subproducts__id=subproduct_id)

    def perform_create(self, serializer):
        subproduct_id = self.kwargs['subproduct_id']
        subproduct = SubProduct.objects.get(pk=subproduct_id)
        serializer.save(subproduct=subproduct)


class BusinessHourRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BusinessHour.objects.all()
    serializer_class = BusinessHourSerializer


# Coupon Views
class CouponListCreateView(generics.ListCreateAPIView):
    serializer_class = CouponSerializer

    def get_queryset(self):
        subproduct_id = self.kwargs['subproduct_id']
        return Coupon.objects.filter(subproducts__id=subproduct_id)

    def perform_create(self, serializer):
        subproduct_id = self.kwargs['subproduct_id']
        subproduct = SubProduct.objects.get(pk=subproduct_id)
        serializer.save(subproduct=subproduct)


class CouponRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer

class SubProductListCreate(generics.ListCreateAPIView):
    queryset = SubProduct.objects.all()
    serializer_class = SubProductSerializer

    def post(self, request, *args, **kwargs):
        print("Datos recibidos:", request.data)

        # Obtener los datos de la solicitud
        name = request.data.get('name')
        phone = request.data.get('phone')
        email = request.data.get('email')
        address = request.data.get('address')
        addressmap = request.data.get('addressmap')
        url = request.data.get('url')
        description = request.data.get('description')
        country = request.data.get('country')
        province = request.data.get('province')
        canton = request.data.get('canton')
        distrito = request.data.get('distrito')
        contact_name = request.data.get('contact_name')
        phone_number = request.data.get('phone_number')
        constitucion = request.data.get('constitucion')
        comercial_activity = request.data.get('comercial_activity')
        pay_method = request.data.get('pay_method')

        # Primero procesamos los productos recibidos como string
        products = request.data.get('products', '')  # Obtener los productos como un string
        print("Productos recibidos como string:", products)

        # Dividir el string en una lista de IDs
        product_ids = products.split(',') if products else []
        print("Productos procesados como lista:", product_ids)

        product_objects = []
        for product_id in product_ids:
            print(f"Procesando producto con ID: {product_id}")
            try:
                product = Product.objects.get(id=product_id)
                print(f"Producto encontrado: {product}")
                product_objects.append(product)
            except Product.DoesNotExist:
                print(f"Producto con ID {product_id} no encontrado.")
                return Response({"error": f"Producto con ID {product_id} no encontrado."}, status=status.HTTP_400_BAD_REQUEST)

        # Verificar que se han agregado productos correctamente
        print("Productos que se van a asociar al subproducto:", product_objects)

        # Crear el subproducto
        with transaction.atomic():
            print("Creando subproducto...")
            subproduct = SubProduct.objects.create(
                name=name, phone=phone, email=email, address=address, addressmap=addressmap, 
                url=url, description=description, country=country, province=province, 
                canton=canton, distrito=distrito, contact_name=contact_name, 
                phone_number=phone_number, constitucion=constitucion, 
                comercial_activity=comercial_activity, pay_method=pay_method
            )
            print(f"Subproducto creado con ID: {subproduct.id}")

            # Asociar los productos procesados al subproducto
            subproduct.products.set(product_objects)

            # Procesar y crear horarios de trabajo
            business_hours_data = request.data.get('business_hours')
            business_hours_ids = []
            if business_hours_data:
                try:
                    business_hours_data = json.loads(business_hours_data)
                    for day, times in business_hours_data.items():
                        business_hour = BusinessHour.objects.create(
                            day=day, start_time=times.get('start'), end_time=times.get('end')
                        )
                        business_hours_ids.append(business_hour.id)
                except json.JSONDecodeError:
                    return Response({"error": "Formato incorrecto en business_hours."}, status=status.HTTP_400_BAD_REQUEST)

            # Procesar y crear miembros del equipo
            team_members_ids = []
            for i in range(len(request.data.getlist('team_members[0][name]'))):
                member = TeamMember.objects.create(
                    name=request.data.get(f'team_members[{i}][name]'),
                    position=request.data.get(f'team_members[{i}][position]'),
                    photo=request.FILES.get(f'team_members[{i}][photo]')
                )
                team_members_ids.append(member.id)

            # Procesar y crear cupones
            coupons_ids = []
            for i in range(len(request.data.getlist('coupons[0][code]'))):
                coupon = Coupon.objects.create(
                    code=request.data.get(f'coupons[{i}][code]'),
                    description=request.data.get(f'coupons[{i}][description]'),
                    image=request.FILES.get(f'coupons[{i}][image]')
                )
                coupons_ids.append(coupon.id)

            # Ahora asociar estos IDs al subproducto
            subproduct.business_hours.set(business_hours_ids)
            subproduct.team_members.set(team_members_ids)
            subproduct.coupons.set(coupons_ids)

            print(f"Subproducto {subproduct.id} asociado con horarios, miembros y cupones.")
            
            return Response({"message": "SubProduct creado correctamente", "subproduct_id": subproduct.id}, status=status.HTTP_201_CREATED)


class SubProductRetrieveUpdate(generics.RetrieveUpdateAPIView):
    queryset = SubProduct.objects.all()
    serializer_class = SubProductSerializer
    

class SubProductDestroy(generics.DestroyAPIView):
    queryset = SubProduct.objects.all()
    serializer_class = SubProductSerializer

    def perform_destroy(self, instance):
        
        product_names = instance.product_names.split(',')
        
        
        if "nombre_producto_a_eliminar" in product_names:
            product_names.remove("nombre_producto_a_eliminar")
        
        instance.product_names = ','.join(product_names)
        instance.delete()


class SubProductCreateOrUpdate(generics.CreateAPIView, generics.UpdateAPIView):
    queryset = SubProduct.objects.all()
    serializer_class = SubProductSerializer

    def perform_create(self, serializer):
        product_id = self.kwargs.get('product_id')
        product = Product.objects.get(pk=product_id)
        serializer.save(product=product)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        product_id = self.kwargs.get('product_id')
        product = Product.objects.get(pk=product_id)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product)
        return Response(serializer.data)

    def add_product_name(self, instance, product_name):
        if not instance.product_names:
            instance.product_names = product_name
        else:
            product_names_list = instance.product_names.split(',')
            if product_name not in product_names_list:
                product_names_list.append(product_name)
                instance.product_names = ','.join(product_names_list)

    def remove_product_name(self, instance, product_name):
        if instance.product_names:
            product_names_list = instance.product_names.split(',')
            if product_name in product_names_list:
                product_names_list.remove(product_name)
                instance.product_names = ','.join(product_names_list)

class ServiceDeleteView(APIView):
    def delete(self, request, subproducts_id, service_id):  
        try:
            service = Service.objects.get(id=service_id, subproduct_id=subproducts_id)  
            service.delete()
            return Response({"message": "Service deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Service.DoesNotExist:
            return Response({"message": "Service not found"}, status=status.HTTP_404_NOT_FOUND)


class SubProductServicesView(generics.ListCreateAPIView):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer

    def get_queryset(self):
        subproduct_id = self.kwargs['subproduct_id']
        return Service.objects.filter(subproduct_id=subproduct_id)

    def put(self, request, subproduct_id, *args, **kwargs):
        service_id = kwargs.get('service_id')
        
        try:
            service = Service.objects.get(id=service_id, subproduct_id=subproduct_id)
        except Service.DoesNotExist:
            return Response({"message": "Service not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ServiceSerializer(service, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, subproduct_id, service_id, *args, **kwargs):
        try:
            service = Service.objects.get(id=service_id, subproduct_id=subproduct_id)
        except Service.DoesNotExist:
            return Response({"message": "Service not found"}, status=status.HTTP_404_NOT_FOUND)

        service.delete()
        return Response({"message": "Service deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
class SubProductServicesList(APIView):
    def get(self, request, subproduct_id):
        try:
            services = Service.objects.filter(subproduct_id=subproduct_id)
            serializer = ServiceSerializer(services, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Service.DoesNotExist:
            return Response({"message": "Services not found for the subproduct"}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, subproduct_id):
        print(request.data)
        try:
            subproduct = SubProduct.objects.get(id=subproduct_id)
        except SubProduct.DoesNotExist:
            return Response({"message": "Subproduct not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ServiceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(subproduct=subproduct)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ComboListCreate(generics.ListCreateAPIView):
    serializer_class = ComboSerializer
    queryset = Combo.objects.all()

    def create(self, request, *args, **kwargs):
        logger.info("Datos recibidos para crear combo: %s", request.data)

        # Validar datos
        name = request.data.get('name')
        description = request.data.get('description')
        price = request.data.get('price')
        selected_service_ids = request.data.get('selectedServiceIds', [])

        # Validaciones y log de errores
        if not name:
            logger.error("Falta el nombre del combo")
            return Response({'error': 'Falta el nombre del combo'}, status=status.HTTP_400_BAD_REQUEST)

        if not description:
            logger.error("Falta la descripción del combo")
            return Response({'error': 'Falta la descripción del combo'}, status=status.HTTP_400_BAD_REQUEST)

        if price is None:
            logger.error("Falta el precio del combo")
            return Response({'error': 'Falta el precio del combo'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            price = float(price)  # Convertir a float
        except ValueError:
            logger.error("El precio debe ser un número válido")
            return Response({'error': 'El precio debe ser un número válido'}, status=status.HTTP_400_BAD_REQUEST)

        if not selected_service_ids:
            logger.error("Faltan IDs de servicios seleccionados")
            return Response({'error': 'Faltan IDs de servicios seleccionados'}, status=status.HTTP_400_BAD_REQUEST)

        # Crear el combo
        combo_data = {
            'name': name,
            'description': description,
            'price': price
        }

        serializer = self.get_serializer(data=combo_data)
        if not serializer.is_valid():
            logger.error("Errores de validación: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        combo = serializer.save()

        # Agregar los servicios seleccionados
        for service_id in selected_service_ids:
            try:
                service = Service.objects.get(id=service_id)
                combo.services.add(service)
            except Service.DoesNotExist:
                logger.error("Servicio con ID %s no existe", service_id)
                return Response({'error': f'Servicio con ID {service_id} no existe'}, status=status.HTTP_400_BAD_REQUEST)

        logger.info("Combo creado exitosamente: %s", combo)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ComboRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Combo.objects.all()
    serializer_class = ComboSerializer


class ProductListCreate(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    queryset = Product.objects.all()

    def perform_create(self, serializer):
        file = self.request.data.get('file')
        file1 = self.request.data.get('file1')
        name = self.request.data.get('name')
        description = self.request.data.get('description')
        characteristics_ids = self.request.data.getlist('characteristics', [])

        if file and name:
            product = serializer.save(user=self.request.user, file=file, file1=file1, name=name, description=description)

            if characteristics_ids:
                try:
                    characteristics_ids = [int(char_id) for char_id in characteristics_ids]
                except ValueError:
                    return Response({'error': 'Invalid characteristic ID(s)'}, status=status.HTTP_400_BAD_REQUEST)

                for char_id in characteristics_ids:
                    try:
                        char = Characteristic.objects.get(pk=char_id)
                        if char not in product.characteristics.all():
                            product.characteristics.add(char)
                    except Characteristic.DoesNotExist:
                        return Response({'error': f'Characteristic with ID {char_id} does not exist'}, status=status.HTTP_400_BAD_REQUEST)
            
        else:
            serializer.save(user=self.request.user)

class ProductRetrieveUpdate(generics.RetrieveUpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        print("Datos recibidos para actualización:", request.data)

        # Extraer y manejar características
        characteristics_data = request.data.get('characteristics', [])
        print("Características recibidas:", characteristics_data)

        if isinstance(characteristics_data, list) and characteristics_data:
            instance.characteristics.clear()  
            for char_data in characteristics_data:
                if isinstance(char_data, dict) and 'id' in char_data:
                    char, _ = Characteristic.objects.get_or_create(
                        id=char_data['id'],
                        defaults={
                            'name': char_data.get('name'),
                            'description': char_data.get('description')
                        }
                    )
                    instance.characteristics.add(char)
                else:
                    print("Datos incorrectos para características:", char_data)
        else:
            print("No se recibieron características o el formato es incorrecto:", characteristics_data)

        serializer.save()
        return Response(serializer.data)




class ProductDestroy(generics.DestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class CharacteristicListCreate(generics.ListCreateAPIView):
    serializer_class = CharacteristicSerializer
    queryset = Characteristic.objects.all()

class CharacteristicRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Characteristic.objects.all()
    serializer_class = CharacteristicSerializer

class CharacteristicDestroy(generics.DestroyAPIView):
    queryset = Characteristic.objects.all()
    serializer_class = CharacteristicSerializer

class SubProductServicesListAll(APIView):
    def get(self, request):
        try:
            services = Service.objects.all()
            serializer = ServiceSerializer(services, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Service.DoesNotExist:
            return Response({"message": "Services not found"}, status=status.HTTP_404_NOT_FOUND)