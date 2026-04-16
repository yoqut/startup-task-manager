"""
JWT authentication middleware for Django Channels WebSocket connections.
Reads the token from the query string: ?token=<access_token>
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError

User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_key):
    try:
        token = AccessToken(token_key)
        user  = User.objects.select_related("company", "dept").get(id=token["user_id"])
        return user if user.is_active else AnonymousUser()
    except (TokenError, User.DoesNotExist, KeyError):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        params       = parse_qs(query_string)
        token_list   = params.get("token", [])
        scope["user"] = await get_user_from_token(token_list[0]) if token_list else AnonymousUser()
        return await super().__call__(scope, receive, send)
