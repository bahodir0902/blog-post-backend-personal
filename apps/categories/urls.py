from django.urls import include, path
from rest_framework import routers

from apps.categories.views import CategoryViewSet

router = routers.DefaultRouter()
router.register("", CategoryViewSet, basename="categories")

urlpatterns = [
    path("", include(router.urls)),
]
