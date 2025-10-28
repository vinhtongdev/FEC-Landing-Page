from django.urls import path
from .views import views as v

urlpatterns = [
    path('', v.DashboardListView.as_view(), name='dashboard'),
    path('customer/<int:pk>/', v.CustomerDetailView.as_view(), name='customer_detail'),
    path('export/csv/', v.export_csv, name='export_csv'),
]
