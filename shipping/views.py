from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework import status
from .models import Product, Review, Order, OrderItem, ShippingAddress, ProductImage, Form, FormField, FormResponse
from .serializers import (
    ProductSerializer,
    ReviewSerializer,
    OrderSerializer,
    OrderItemSerializer,
    ShippingAddressSerializer,
    OrderItemWriteSerializer,
    ProductImageSerializer,
    FormSerializer, FormFieldSerializer, 
    FormResponseSerializer
)
from rest_framework.permissions import AllowAny




class ProductFormResponseView(generics.CreateAPIView):
    serializer_class = FormResponseSerializer

    def perform_create(self, serializer):
        product_id = self.kwargs['product_id']  # Obtener el ID del producto desde la URL
        product = Product.objects.get(pk=product_id)
        
        # Asumiendo que 'responses' es un campo que contiene una lista de respuestas
        responses_data = self.request.data.get('responses', [])
        for response in responses_data:
            form_field_id = response['form_field']
            value = response['value']
            form_field = FormField.objects.get(pk=form_field_id)  # Asegúrate de que el form_field existe
            # Crear la respuesta individualmente
            FormResponse.objects.create(
                product=product,
                user=self.request.user,
                form_field=form_field,
                value=value
            )

class ProductFormView(APIView):
    serializer_class = FormSerializer

    def perform_create(self, serializer):
        product_id = self.kwargs['product_id']  # Obtener el ID del producto desde la URL
        product = Product.objects.get(pk=product_id)
        serializer.save(product=product)

    def get(self, request, product_id):
        try:
            product = Product.objects.get(_id=product_id)
            forms = Form.objects.filter(product=product)
            serializer = FormSerializer(forms, many=True)
            return Response(serializer.data)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, product_id):
        try:
            product = Product.objects.get(_id=product_id)
            form_data = request.data.get('form')
            form_serializer = FormSerializer(data=form_data)
            if form_serializer.is_valid():
                form_serializer.save(product=[product])
                return Response(form_serializer.data, status=status.HTTP_201_CREATED)
            return Response(form_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

# Vista para listar y crear campos de formularios
class FormFieldListCreateView(generics.ListCreateAPIView):
    serializer_class = FormFieldSerializer

    def get_queryset(self):
        form_id = self.kwargs['form_id']
        return FormField.objects.filter(form_id=form_id)

    def perform_create(self, serializer):
        form_id = self.kwargs['form_id']
        serializer.save(form_id=form_id)

# Vista para obtener, actualizar y eliminar campos de formularios
class FormFieldRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FormField.objects.all()
    serializer_class = FormFieldSerializer
    lookup_field = 'pk'

    def get_queryset(self):
        form_id = self.kwargs['form_id']
        return FormField.objects.filter(form_id=form_id)
    
# Vistas para formularios
class FormListCreateView(generics.ListCreateAPIView):
    queryset = Form.objects.all()
    serializer_class = FormSerializer

    def create(self, request, *args, **kwargs):
        # Permitir la creación de un formulario sin fields ni products
        # Puedes usar `partial=True` para hacer la creación parcialmente
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class FormRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Form.objects.all()
    serializer_class = FormSerializer
    permission_classes = [permissions.IsAuthenticated]

# Vistas para respuestas de formularios
class FormResponseListCreateView(generics.ListCreateAPIView):
    queryset = FormResponse.objects.all()
    serializer_class = FormResponseSerializer

    def perform_create(self, serializer):
        print("Datos recibidos:", self.request.data)  
        form_data = self.request.data
        responses = form_data.get('responses', [])

        # Si 'responses' es un solo diccionario, conviértelo en una lista
        if isinstance(responses, dict):
            responses = [responses]

        for response in responses:
            serializer.save(
                form_id=form_data['form'],
                product_id=form_data['product'],
                user_id=form_data['user'],
                form_field=response['form_field'],
                value=response['value']
            )

    def post(self, request, *args, **kwargs):
        print("Datos recibidos:", self.request.data)  
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # Valida los datos
        
        self.perform_create(serializer)  # Guarda los datos
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class FormResponseDeleteView(generics.DestroyAPIView):
    queryset = FormResponse.objects.all()
    serializer_class = FormResponseSerializer

    def delete(self, request, *args, **kwargs):
        try:
            instance = self.get_object()  # Obtener el objeto usando el ID
            instance.delete()  # Eliminar el objeto
            return Response(status=status.HTTP_204_NO_CONTENT)  # Retornar 204 No Content en caso de éxito
        except FormResponse.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND) 
                
class FormResponseRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FormResponse.objects.all()
    serializer_class = FormResponseSerializer
    permission_classes = [permissions.IsAuthenticated]
    
class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def perform_create(self, serializer):
        # Asigna el usuario autenticado automáticamente
        serializer.save(user=self.request.user)
        
class ProductRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    

class ReviewListCreateView(generics.ListCreateAPIView):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class ReviewRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class ProductImageListCreateView(generics.ListCreateAPIView):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [AllowAny]
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class ProductImageRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class OrderListCreateView(generics.ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        # Custom logic to handle adding products to the order
        product_ids = request.data.get('product_ids', [])
        products = Product.objects.filter(pk__in=product_ids)

        order_serializer = self.get_serializer(data=request.data)

        if order_serializer.is_valid(raise_exception=True):
            order_instance = order_serializer.save(user=self.request.user)
            order_instance.product.set(products)

            return Response(order_serializer.data, status=status.HTTP_201_CREATED)

        return Response({'detail': 'Error in creating order with products'}, status=status.HTTP_400_BAD_REQUEST)

class OrderRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

class OrderItemCreateView(generics.CreateAPIView):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemWriteSerializer


    def get(self, request, *args, **kwargs):
        order_items = OrderItem.objects.all()
        serializer = OrderItemSerializer(order_items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class OrderItemRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]

class ShippingAddressCreateView(generics.CreateAPIView):
    queryset = ShippingAddress.objects.all()
    serializer_class = ShippingAddressSerializer


    def get(self, request, *args, **kwargs):
        shipping_addresses = ShippingAddress.objects.all()
        serializer = ShippingAddressSerializer(shipping_addresses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ShippingAddressRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ShippingAddress.objects.all()
    serializer_class = ShippingAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

class UpdateNumReviewsView(generics.UpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    # permission_classes = [permissions.IsAuthenticated]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.numReviews += 1  # Incrementa el número de revisiones
        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)
