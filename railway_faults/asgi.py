import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
import faults.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "railway_faults.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            faults.routing.websocket_urlpatterns
        )
    ),
})
