from rest_framework import generics
from .models import Property, Booking, Payment, Review, Amenity, PropertyImage
from .serializers import PropertySerializer, BookingSerializer, PaymentSerializer, ReviewSerializer, AmenitySerializer, PropertyImageSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError

# Vistas para Amenidades
class AmenityListCreate(generics.ListCreateAPIView):
    queryset = Amenity.objects.all()
    serializer_class = AmenitySerializer

class AmenityRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Amenity.objects.all()
    serializer_class = AmenitySerializer

# Vistas para Property
class PropertyListCreate(generics.ListCreateAPIView):
    serializer_class = PropertySerializer
    queryset = Property.objects.all()
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # Ajustar datos si es necesario
        data = request.data

        # Convertir 'amenities[]' a 'amenities' como lista
        amenities = data.getlist('amenities[]')  # Extraer las amenidades como lista.
        if amenities:
            data.setlist('amenities', amenities)

        # Pasar los datos ajustados al serializer
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class PropertyImageList(generics.ListAPIView):
    queryset = PropertyImage.objects.all()
    serializer_class = PropertyImageSerializer

class PropertyRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Property.objects.all()
    serializer_class = PropertySerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        # Obtener imágenes de la solicitud
        images = request.FILES.getlist('images')

        # Serializar y actualizar la propiedad
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Crear instancias de imágenes relacionadas
        for image in images:
            PropertyImage.objects.create(property=instance, image=image)

        return Response(serializer.data)

# Vistas para Booking
class BookingListCreate(generics.ListCreateAPIView):
    serializer_class = BookingSerializer
    queryset = Booking.objects.all()
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        # Imprimir los datos recibidos en la solicitud
        print("Datos recibidos:", request.data)  # Esto mostrará los datos recibidos

        try:
            # Intentar crear el booking
            return super().create(request, *args, **kwargs)
        except ValidationError as e:
            # Imprimir el error de validación
            print("Error de validación:", e.detail)  # Esto mostrará los detalles del error
            # Retornar un error 400 con los detalles del fallo
            return Response({'errors': e.detail}, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        serializer.save(guest=self.request.user)

class BookingRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

# Vistas para Payment
class PaymentListCreate(generics.ListCreateAPIView):
    serializer_class = PaymentSerializer
    queryset = Payment.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class PaymentRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

# Vistas para Review
class ReviewListCreate(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    queryset = Review.objects.all()
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ReviewRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
