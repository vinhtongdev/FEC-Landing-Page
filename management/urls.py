from django.urls import path
from . import views

urlpatterns = [
    path('', views.DashboardListView.as_view(), name='dashboard'),
    path('customer/<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('export/csv/', views.export_csv, name='export_csv'),
    path('download/<int:pk>/', views.download_file, name='download_file'),
]