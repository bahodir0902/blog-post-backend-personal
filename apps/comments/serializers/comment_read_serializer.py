from rest_framework import serializers

from apps.comments.models import Comment
from apps.posts.serializers.posts.posts import AuthorSerializer


class CommentReadSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    reply_count = serializers.SerializerMethodField()
    likes = serializers.IntegerField(read_only=True)
    dislikes = serializers.IntegerField(read_only=True)
    user_reaction = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "post",
            "author",
            "parent",
            "content",
            "is_edited",
            "is_deleted",
            "created_at",
            "updated_at",
            "reply_count",
            "likes",
            "dislikes",
            "user_reaction",
            # "replies",
        ]
        read_only_fields = ["author", "is_edited", "is_deleted"]

    def get_reply_count(self, obj: Comment):
        return getattr(obj, "reply_count", obj.replies.count())

    def get_user_reaction(self, obj: Comment):
        user_reactions = getattr(obj, "user_reactions", None)
        if user_reactions:
            return user_reactions[0].reaction

        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        # fallback
        reaction = obj.reactions.filter(user=request.user).first()
        return reaction.reaction if reaction else None


class RepliesForCommentSerializer(serializers.Serializer):
    def to_representation(self, instance):
        return CommentReadSerializer(instance).data
