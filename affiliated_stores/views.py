from rest_framework import generics
from .models import Property, Review
from .serializers import PropertySerializer, ReviewSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated

# Vistas para Property
class PropertyListCreate(generics.ListCreateAPIView):
    serializer_class = PropertySerializer
    queryset = Property.objects.all()
    permission_classes = [AllowAny]  # Puedes ajustar a IsAuthenticated si es necesario

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class PropertyRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Property.objects.all()
    serializer_class = PropertySerializer

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
