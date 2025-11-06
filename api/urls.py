from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, CustomerViewSet, OrderViewSet, PaymentViewSet, PromotionViewSet,
    CustomerPointsViewSet, ProductionQueueViewSet, SignupAPIView,PointsConfigViewSet,
    LoginAPIView, ResetPasswordAPIView, ResetPasswordUser, InactiveOrdersAPIView,
    DashboardAPIView, ProductionQueueDashboardAPIView
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'customers', CustomerViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'promotions', PromotionViewSet)
router.register(r'customer-points', CustomerPointsViewSet)
router.register(r'production-queues', ProductionQueueViewSet)
router.register(r'points-config', PointsConfigViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('signup/', SignupAPIView.as_view(), name='signup'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('reset_password/', ResetPasswordAPIView.as_view(), name='reset_password'),
    path('reset_password_user/<str:reset_token>/', ResetPasswordUser.as_view(), name='reset_password_user'),
    path('inactive-orders/', InactiveOrdersAPIView.as_view(), name='inactive_orders'),
    path('dashboard/', DashboardAPIView.as_view(), name='dashboard'),
    path('production-queue-dashboard/', ProductionQueueDashboardAPIView.as_view(), name='production_queue_dashboard'),
    path('orders/<int:pk>/add_payment/', OrderViewSet.as_view({'post': 'add_payment'}), name='order-add-payment'),
    path('orders/<int:pk>/events/<int:event_id>/', OrderViewSet.as_view({'put': 'update_event', 'delete': 'delete_event'}), name='order-event-detail'),
    path('orders/<int:pk>/add_payment/', OrderViewSet.as_view({'post': 'add_payment'}), name='order-add-payment'),
]