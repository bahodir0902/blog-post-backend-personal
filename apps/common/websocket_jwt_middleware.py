import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)
User = get_user_model()


class WebsocketJWTMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)

        token = params.get("token", [None])[0]
        scope["user"] = AnonymousUser()

        if token:
            try:
                access_token = AccessToken(token)
                user_id = access_token["user_id"]
                scope["user"] = await self.get_user(user_id)
            except Exception as e:
                print(f"Error: {e}")
                logger.warning(f"[Websocket middleware] warning: {e}")

        return await self.app(scope, receive, send)

    @database_sync_to_async
    def get_user(self, user_id: int):
        return User.objects.get(pk=user_id)
