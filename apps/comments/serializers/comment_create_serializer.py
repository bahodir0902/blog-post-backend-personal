from rest_framework import serializers

from apps.comments.models import Comment


class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["parent", "content"]

    # def validate(self, attrs):
    #     parent = attrs.get("parent")
    #     if parent and parent.parent and parent.parent.parent:
    #         raise serializers.ValidationError("Max reply depth reached.")
    #     return attrs
