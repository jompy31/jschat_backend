from django.urls import path
from .views import (
    PropertyListCreate,
    PropertyRetrieveUpdateDestroy,
    BookingListCreate,
    BookingRetrieveUpdateDestroy,
    PaymentListCreate,
    PaymentRetrieveUpdateDestroy,
    ReviewListCreate,
    ReviewRetrieveUpdateDestroy,
    AmenityListCreate,
    AmenityRetrieveUpdateDestroy,
    PropertyImageList
)

urlpatterns = [
    # Properties
    path('properties/', PropertyListCreate.as_view(), name='property-list-create'),
    path('property-images/', PropertyImageList.as_view(), name='property-image-list'),
    path('properties/<int:pk>/', PropertyRetrieveUpdateDestroy.as_view(), name='property-retrieve-update-destroy'),

    # Bookings
    path('bookings/', BookingListCreate.as_view(), name='booking-list-create'),
    path('bookings/<int:pk>/', BookingRetrieveUpdateDestroy.as_view(), name='booking-retrieve-update-destroy'),

    # Payments
    path('payments/', PaymentListCreate.as_view(), name='payment-list-create'),
    path('payments/<int:pk>/', PaymentRetrieveUpdateDestroy.as_view(), name='payment-retrieve-update-destroy'),

    # Reviews
    path('reviews/', ReviewListCreate.as_view(), name='review-list-create'),
    path('reviews/<int:pk>/', ReviewRetrieveUpdateDestroy.as_view(), name='review-retrieve-update-destroy'),

    # Amenities
    path('amenities/', AmenityListCreate.as_view(), name='amenity-list-create'),
    path('amenities/<int:pk>/', AmenityRetrieveUpdateDestroy.as_view(), name='amenity-retrieve-update-destroy'),
]
