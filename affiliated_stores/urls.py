from django.urls import path
from .views import (
    PropertyListCreate,
    PropertyRetrieveUpdateDestroy,
    ReviewListCreate,
    ReviewRetrieveUpdateDestroy,
)

urlpatterns = [
    # Rutas para Property (GET, POST, PUT, DELETE)
    path('properties/', PropertyListCreate.as_view(), name='property-list-create'),  # GET, POST
    path('properties/<int:pk>/', PropertyRetrieveUpdateDestroy.as_view(), name='property-detail'),  # GET, PUT, DELETE

    # Rutas para Review (GET, POST, PUT, DELETE)
    path('reviews/', ReviewListCreate.as_view(), name='review-list-create'),  # GET, POST
    path('reviews/<int:pk>/', ReviewRetrieveUpdateDestroy.as_view(), name='review-detail'),  # GET, PUT, DELETE
]
