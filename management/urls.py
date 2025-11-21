from django.urls import path
from . import views

app_name = 'management'

urlpatterns = [
    path('', views.DashboardListView.as_view(), name='dashboard'),
    path('customer/<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('export/csv/', views.export_csv, name='export_csv'),
    path('download/<int:pk>/', views.download_file, name='download_file'),
    
    path("customer/<int:pk>/edit/", views.customer_edit, name="customer_edit"),
    path("customer/<int:pk>/save/", views.customer_save_changes, name="customer_save_changes"),
    path("approval/<int:approval_id>/verify/", views.approval_verify_and_apply, name="approval_verify"),
    path("push/subscribe/", views.push_subscribe, name="push_subscribe"),
]