import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

try:
    django_asgi_app = get_asgi_application()
except Exception as e:
    import traceback
    traceback.print_exc()
    raise e

from channels.routing import ProtocolTypeRouter, URLRouter # noqa
from channels.auth import AuthMiddlewareStack # noqa

from main.urls import websocket_urlpatterns # noqa


application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})