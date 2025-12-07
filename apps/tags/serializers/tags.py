from rest_framework import serializers

from apps.tags.models import Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug", "created_at"]
        extra_kwargs = {
            "id": {"read_only": True},
            "created_at": {"read_only": True},
        }
