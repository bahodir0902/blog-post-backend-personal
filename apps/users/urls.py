from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AuthViewSet,
    CheckTokenBeforeObtainView,
    CustomTokenRefreshView,
    UserViewSet,
)

router = DefaultRouter()
router.register(r"auth", AuthViewSet, basename="auth")
router.register(r"user", UserViewSet, basename="user")

app_name = "users"

urlpatterns = [
    path("login/", CheckTokenBeforeObtainView.as_view(), name="login"),
    path("login/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("", include(router.urls)),
]
