from rest_framework import serializers

from apps.notifications.models import CommentNotification
from apps.users.serializers import PublicUserSerializer


class CommentNotificationReadSerializer(serializers.ModelSerializer):
    sender = PublicUserSerializer(read_only=True)
    receiver = PublicUserSerializer(read_only=True)
    post = serializers.CharField(source="comment.post.title", read_only=True)
    post_slug = serializers.CharField(source="comment.post.slug", read_only=True)
    comment_id = serializers.IntegerField(
        source="comment.id", read_only=True
    )  # ADD THIS (explicit)
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = CommentNotification
        fields = [
            "id",
            "sender",
            "receiver",
            "post",
            "post_slug",
            "comment",
            "comment_id",
            "message",
            "is_read",
            "unread_count",
            "created_at",
            "updated_at",
        ]

    def get_unread_count(self, obj: CommentNotification):
        return self.context.get("unread_count", 0)


class MarkAsReadSerializer(serializers.Serializer):
    ids = serializers.ListSerializer(child=serializers.IntegerField(), required=True)

    def validate(self, attrs):
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        ids = self.validated_data.pop("ids")
        qs = CommentNotification.objects.filter(id__in=ids, receiver_id=user.pk, is_read=False)
        return qs.update(is_read=True)


class DeleteCommentNotificationSerializer(serializers.Serializer):
    ids = serializers.ListSerializer(
        child=serializers.IntegerField(),
        required=True,
        help_text="List of notification IDs to delete",
    )

    def validate_ids(self, value):
        if not value:
            raise serializers.ValidationError("At least one notification ID is required")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        ids = self.validated_data["ids"]

        qs = CommentNotification.objects.filter(id__in=ids, receiver_id=user.pk)

        deleted_count, _ = qs.delete()
        return deleted_count
