from django.urls import re_path
from .consumers import DashboardCustomerConsumer

websocket_urlpatterns = [
    re_path(r'ws/dashboard/customers/$', DashboardCustomerConsumer.as_asgi()),
]

#