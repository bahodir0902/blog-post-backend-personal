from drf_spectacular.utils import extend_schema
from rest_framework import mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from apps.favourites.models import Favourite
from apps.posts.models import Post

from .serializers import FavouriteSerializer


@extend_schema(tags=["List Favourites"])
class FavouriteViewSet(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FavouriteSerializer

    def get_queryset(self):
        # TODO with post statuses
        qs = (
            Favourite.objects.filter(user=self.request.user, post__status=Post.Status.PUBLISHED)
            .select_related("user", "post")
            .prefetch_related("post__images")
            .order_by("-created_at")
        )

        return qs
