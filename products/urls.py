from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductTypeViewSet, CharacteristicViewSet, ProductViewSet

router = DefaultRouter()
router.register(r'product-types', ProductTypeViewSet)
router.register(r'characteristics', CharacteristicViewSet)
router.register(r'products', ProductViewSet)

urlpatterns = [
    path('', include(router.urls)),
]