from rest_framework import serializers

from apps.favourites.models import Favourite
from apps.posts.serializers import PostListSerializer


class FavouriteSerializer(serializers.ModelSerializer):
    post = PostListSerializer(read_only=True)

    class Meta:
        model = Favourite
        fields = ["id", "user", "post", "created_at", "updated_at"]
        extra_kwargs = {
            "id": {"read_only": True},
            "user": {"read_only": True},
        }
