from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FavouriteViewSet

router = DefaultRouter()
router.register("", FavouriteViewSet, basename="favourites")

urlpatterns = [
    path("", include(router.urls)),
]
