from rest_framework import serializers

from apps.bookmarks.models import Bookmark
from apps.posts.serializers import PostListSerializer


class BookmarkSerializer(serializers.ModelSerializer):
    post = PostListSerializer(read_only=True)

    class Meta:
        model = Bookmark
        fields = ["id", "user", "post", "created_at", "updated_at"]
        extra_kwargs = {
            "id": {"read_only": True},
            "user": {"read_only": True},
        }
