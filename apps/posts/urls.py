from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter

from apps.comments.views import CommentViewSet

from .views import AuthorPostViewSet, ClientPostViewSet

router = DefaultRouter()
router.register("author", AuthorPostViewSet, basename="author")
router.register("client", ClientPostViewSet, basename="client")

client_router = NestedDefaultRouter(router, "client", lookup="post")
client_router.register("comments", CommentViewSet, basename="client-comments")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(client_router.urls)),
]
