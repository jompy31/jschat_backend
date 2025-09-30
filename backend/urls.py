from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from api.views import EmailAPIView

urlpatterns = [
    path('api/', include([
        path('admin/', admin.site.urls),
        path('', include('api.urls')),
        path('files/', include('files.urls')),
        path('products/', include('products.urls')),
        # path('shipping/', include('shipping.urls')),
        # path('employee/', include('employee.urls')),
        # path('tourism/', include('tourism.urls')),
        # path('affiliated_stores/', include('affiliated_stores.urls')),
        # path('news/', include('news.urls')),
        path('send-email/', EmailAPIView.as_view()),
    ])),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
