from django.urls import re_path
from .consumers import FaultsConsumer

websocket_urlpatterns = [
    re_path(r"^ws/faults/$", FaultsConsumer.as_asgi()),
]
