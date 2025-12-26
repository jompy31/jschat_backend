from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import ProductType, Characteristic, Product
from .serializers import ProductTypeSerializer, CharacteristicSerializer, ProductSerializer
from api.models import UserProfile
from django.contrib.auth.models import User
import json
import logging

logger = logging.getLogger(__name__)

class IsAdminOrSalesOrDesign(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        profile = UserProfile.objects.filter(user=request.user).first()
        logger.debug(f"Usuario: {request.user}, Perfil: {profile}, staff_status: {profile.staff_status if profile else None}")
        return profile and profile.staff_status in ['administrator', 'sales', 'design']

class ProductTypeViewSet(viewsets.ModelViewSet):
    queryset = ProductType.objects.all()
    serializer_class = ProductTypeSerializer 
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [IsAdminOrSalesOrDesign()]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class CharacteristicViewSet(viewsets.ModelViewSet):
    queryset = Characteristic.objects.all()
    serializer_class = CharacteristicSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [IsAdminOrSalesOrDesign()]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [IsAdminOrSalesOrDesign()]
    
    def dispatch(self, request, *args, **kwargs):
        # === DEBUG: Información de la solicitud ===
        logger.debug("="*60)
        logger.debug(f"MÉTODO: {request.method}")
        logger.debug(f"URL: {request.path}")
        logger.debug(f"Content-Type: {request.content_type}")
        logger.debug(f"request.FILES: {bool(request.FILES)}")
        # logger.debug(f"request.body (raw): {type(request.body)} -> {len(request.body) if request.body else 0} bytes")
        # Extract request data safely
        # data = getattr(request, 'data', request.POST or request.body)
        # if isinstance(data, bytes):
        #     try:
        #         data = json.loads(data.decode('utf-8'))
        #     except json.JSONDecodeError:
        #         data = request.POST or {}
        # logger.debug(f"Solicitud recibida en ProductViewSet: Método={request.method}, URL={request.path}, Datos={data}, Archivos={request.FILES}")
        return super().dispatch(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        logger.info(f"Solicitud POST recibida en ProductViewSet.create: Datos={request.data}, Archivos={request.FILES}")
        
        # ETL Process
        # Extract: Get raw data from request
        data = request.data.dict() if hasattr(request.data, 'dict') else dict(request.data)
        
        # Handle design_file from request.FILES
        if 'design_file' in request.FILES:
            data['design_file'] = request.FILES['design_file']
        elif 'design_file' in data and (data['design_file'] == '' or data['design_file'] is None or data['design_file'] == '{}'):
            data['design_file'] = None
        
        # Transform: Preprocess data to handle various input formats
        try:
            # Handle product_type_id
            if 'product_type_id' in data:
                try:
                    data['product_type_id'] = int(data['product_type_id'])
                except (ValueError, TypeError):
                    logger.error(f"Invalid product_type_id: {data['product_type_id']}")
                    return Response(
                        {"product_type_id": "Must be a valid integer"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Handle created_by_id
            if 'created_by_id' in data:
                try:
                    data['created_by_id'] = int(data['created_by_id'])
                except (ValueError, TypeError):
                    logger.error(f"Invalid created_by_id: {data['created_by_id']}")
                    return Response(
                        {"created_by_id": "Must be a valid integer"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Handle characteristic_ids using getlist to support multi-valued fields
            if 'characteristic_ids' in request.data:
                characteristic_ids = request.data.getlist('characteristic_ids')
                if characteristic_ids:
                    if len(characteristic_ids) == 1:
                        # Try to parse as JSON if single value
                        try:
                            parsed = json.loads(characteristic_ids[0])
                            if isinstance(parsed, list):
                                characteristic_ids = parsed
                            else:
                                # If parsed but not list (e.g., single number), treat as list
                                characteristic_ids = [parsed]
                        except json.JSONDecodeError:
                            # Not JSON, treat as single string ID
                            characteristic_ids = [characteristic_ids[0]]
                    # If multiple values, treat as list of string IDs
                    # Convert to list of integers
                    try:
                        data['characteristic_ids'] = [int(cid) for cid in characteristic_ids]
                    except ValueError as e:
                        logger.error(f"Invalid characteristic_ids: {characteristic_ids}, Error: {str(e)}")
                        return Response(
                            {"characteristic_ids": "All values must be valid integers"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
            
            # Handle additional_price
            if 'additional_price' in data:
                try:
                    data['additional_price'] = float(data['additional_price'])
                except (ValueError, TypeError):
                    logger.error(f"Invalid additional_price: {data['additional_price']}")
                    return Response(
                        {"additional_price": "Must be a valid decimal number"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        
        except Exception as e:
            logger.error(f"Error during data transformation: {str(e)}")
            return Response(
                {"error": f"Data transformation failed: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Load: Pass transformed data to serializer
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            self.perform_create(serializer)
            logger.info(f"Producto creado exitosamente: {serializer.data}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            logger.error(f"Errores de validación en ProductSerializer: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def perform_create(self, serializer):
        logger.debug(f"Llegó a ProductViewSet.perform_create: Datos validados={serializer.validated_data}")
        serializer.save(created_by=self.request.user)