from django.urls import re_path

from .consumers import CommentNotificationConsumer

notification_urlpatterns = [
    re_path(r"ws/notifications/comments/$", CommentNotificationConsumer.as_asgi())
]
