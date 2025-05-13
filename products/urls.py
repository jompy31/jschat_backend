from django.urls import path
from . import views
from .views import (
    TeamMemberListCreateView,
    TeamMemberRetrieveUpdateDestroyView,
    BusinessHourListCreateView,
    BusinessHourRetrieveUpdateDestroyView,
    CouponListCreateView,
    CouponRetrieveUpdateDestroyView,
    SubProductByEmailView,
)

urlpatterns = [
    path('', views.ProductListCreate.as_view()),
    path('<int:pk>/', views.ProductRetrieveUpdate.as_view()),
    path('product/<int:pk>/delete/', views.ProductDestroy.as_view()),
    path('<int:pk>/update/', views.ProductRetrieveUpdate.as_view()),
    
    path('subproducts/', views.SubProductListCreate.as_view(), name='subproduct-list-create'),
    path('subproducts/<int:pk>/', views.SubProductRetrieveUpdate.as_view(), name='subproduct-retrieve-update'),
    path('subproducts/<int:pk>/delete/', views.SubProductDestroy.as_view(), name='subproduct-destroy'),
    path('subproducts/by-email/<str:email>/', SubProductByEmailView.as_view(), name='subproduct-by-email'),  # New endpoint
    path('subproducts/<int:subproduct_id>/services/', views.SubProductServicesView.as_view(), name='subproduct-services'),
    path('subproducts/<int:subproducts_id>/services/<int:service_id>/', views.ServiceDeleteView.as_view()),

    path('services/', views.SubProductServicesListAll.as_view(), name='all-services-list'),

    path('combos/', views.ComboListCreate.as_view(), name='combo-list-create'),
    path('combos/<int:pk>/', views.ComboRetrieveUpdateDestroy.as_view(), name='combo-retrieve-update-destroy'),

    path('subproducts/<int:subproduct_id>/teammembers/', TeamMemberListCreateView.as_view(), name='teammember-list-create'),
    path('subproducts/<int:subproduct_id>/teammembers/<int:pk>/', TeamMemberRetrieveUpdateDestroyView.as_view(), name='teammember-detail'),
    path('subproducts/<int:subproduct_id>/businesshours/', BusinessHourListCreateView.as_view(), name='businesshour-list-create'),
    path('subproducts/<int:subproduct_id>/businesshours/<int:pk>/', BusinessHourRetrieveUpdateDestroyView.as_view(), name='businesshour-detail'),
    path('subproducts/<int:subproduct_id>/coupons/', CouponListCreateView.as_view(), name='coupon-list-create'),
    path('subproducts/<int:subproduct_id>/coupons/<int:pk>/', CouponRetrieveUpdateDestroyView.as_view(), name='coupon-detail'),

    path('characteristics/', views.CharacteristicListCreate.as_view(), name='characteristic-list-create'),
    path('characteristics/<int:pk>/', views.CharacteristicRetrieveUpdateDestroy.as_view(), name='characteristic-retrieve-update-destroy'),
    path('characteristics/<int:pk>/delete/', views.CharacteristicDestroy.as_view(), name='characteristic-destroy'),
]
