# ITV_FEC_ICustomer/management/routing.py
from django.urls import re_path
from .consumers import  HubConsumer
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from django.urls import path

websocket_urlpatterns = [
    path("ws/hub/", HubConsumer.as_asgi()),
]
