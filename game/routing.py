from django.urls import path
from .consumers import WSConsumer

ws_urlpatterns = [
    path('ws/some_url/<str:player_id>/', WSConsumer.as_asgi()),
]
