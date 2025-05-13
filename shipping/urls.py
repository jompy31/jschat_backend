from django.urls import path
from .views import (
    FormListCreateView,
    FormRetrieveUpdateDestroyView,
    ProductListCreateView,
    ProductRetrieveUpdateDestroyView,
    ReviewListCreateView,
    ReviewRetrieveUpdateDestroyView,
    OrderListCreateView,
    OrderRetrieveUpdateDestroyView,
    OrderItemCreateView,
    OrderItemRetrieveUpdateDestroyView,
    ShippingAddressCreateView,
    ShippingAddressRetrieveUpdateDestroyView,
    ProductImageListCreateView,
    UpdateNumReviewsView, 
    ProductImageRetrieveUpdateDestroyView,
    FormListCreateView,
    FormRetrieveUpdateDestroyView,
    FormResponseListCreateView,
    FormResponseRetrieveUpdateDestroyView,
    FormFieldListCreateView,
    FormFieldRetrieveUpdateDestroyView,
    ProductFormView,
    ProductFormResponseView,
    FormResponseDeleteView,
)

urlpatterns = [
    # Products
    path('products/', ProductListCreateView.as_view(), name='product-list-create'),
    path('products/<int:pk>/', ProductRetrieveUpdateDestroyView.as_view(), name='product-retrieve-update-destroy'),
    path('products/<int:pk>/update-num-reviews/', UpdateNumReviewsView.as_view(), name='update-num-reviews'),
    path('products/<int:product_id>/form/', ProductFormView.as_view(), name='product-form'),
    path('products/<int:product_id>/form/responses/', ProductFormResponseView.as_view(), name='product-form-responses'),

    # ProductImage
    path('product-image/', ProductImageListCreateView.as_view(), name='product-image-list-create'),
    path('product-image/<int:pk>/', ProductImageRetrieveUpdateDestroyView.as_view(), name='product-image-retrieve-update-destroy'),

    # Reviews
    path('reviews/', ReviewListCreateView.as_view(), name='review-list-create'),
    path('reviews/<int:pk>/', ReviewRetrieveUpdateDestroyView.as_view(), name='review-retrieve-update-destroy'),

    # Orders
    path('orders/', OrderListCreateView.as_view(), name='order-list-create'),
    path('orders/<int:pk>/', OrderRetrieveUpdateDestroyView.as_view(), name='order-retrieve-update-destroy'),

    # Order Items
    path('order-items/', OrderItemCreateView.as_view(), name='order-item-create'),
    path('order-items/<int:pk>/', OrderItemRetrieveUpdateDestroyView.as_view(), name='order-item-retrieve-update-destroy'),

    # Shipping Addresses
    path('shipping-addresses/', ShippingAddressCreateView.as_view(), name='shipping-address-create'),
    path('shipping-addresses/<int:pk>/', ShippingAddressRetrieveUpdateDestroyView.as_view(), name='shipping-address-retrieve-update-destroy'),
    
     # Forms
    path('forms/', FormListCreateView.as_view(), name='form-list-create'),
    path('forms/<int:pk>/', FormRetrieveUpdateDestroyView.as_view(), name='form-retrieve-update-destroy'),

    # Form Fields
    path('forms/<int:form_id>/fields/', FormFieldListCreateView.as_view(), name='form-field-list-create'),
    path('forms/<int:form_id>/fields/<int:pk>/', FormFieldRetrieveUpdateDestroyView.as_view(), name='form-field-retrieve-update-destroy'),

    # Form Responses
    path('form-responses/', FormResponseListCreateView.as_view(), name='form-response-list-create'),
    path('form-responses/<int:pk>/', FormResponseRetrieveUpdateDestroyView.as_view(), name='form-response-retrieve-update-destroy'),
    path('form-response/<int:pk>/', FormResponseDeleteView.as_view(), name='form_response_delete')

]
