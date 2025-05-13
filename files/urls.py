from django.urls import path
from . import views

urlpatterns = [
    path('', views.FileListCreate.as_view()),
    path('<int:pk>/', views.FileRetrieveUpdateDestroy.as_view()),
    path('file/<int:pk>/delete/', views.FileDestroy.as_view()), 
    path('news/', views.NewsPostListCreate.as_view()),
    path('news/<int:pk>/', views.NewsPostRetrieveUpdateDestroy.as_view()),
    path('distributors/', views.DistributorListCreate.as_view()),
    path('distributors/<int:pk>/', views.DistributorRetrieveUpdateDestroy.as_view()),
    path('distributors/<int:distributor_id>/services/', views.DistributorServicesList.as_view()),
    path('distributors/<int:distributor_id>/services/<int:service_id>/', views.ServiceDeleteView.as_view()),
    path('designs/', views.DesignListCreate.as_view(), name='design-list-create'),
    path('designs/<int:pk>/', views.DesignRetrieveUpdateDestroy.as_view(), name='design-retrieve-update-destroy'),
    
]