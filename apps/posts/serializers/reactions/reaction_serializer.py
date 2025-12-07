from rest_framework import serializers

from apps.posts.models import Post, Reaction, ReactionType


class ReactionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReactionType
        fields = [
            "id",
            "name",
            "emoji",
        ]
        read_only_fields = ["id"]


class ReactionPutSerializer(serializers.Serializer):
    type = serializers.IntegerField()

    def validate_type(self, value):
        if not ReactionType.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Reaction type does not exist")
        return value

    def validate(self, attrs):
        post: Post | None = self.context.get("post")
        reaction_type_id: int = attrs["type"]
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if post is None or not user:
            raise serializers.ValidationError("Post or request context is required.")

        allowed_ids = set(post.allowed_reactions.values_list("id", flat=True))
        if not allowed_ids:  # Empty means no reactions allowed
            raise serializers.ValidationError("Reactions are not allowed for this post.")

        if post.allowed_reactions.exists():
            allowed_ids = set(post.allowed_reactions.values_list("id", flat=True))
            if reaction_type_id not in allowed_ids:
                raise serializers.ValidationError(
                    "This reaction type is not allowed for this post."
                )
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        post: Post = self.context["post"]
        reaction_type_id: int = validated_data["type"]
        reaction_type: ReactionType = ReactionType.objects.get(pk=reaction_type_id)

        reaction, _ = Reaction.objects.update_or_create(
            user=user, post=post, defaults={"type": reaction_type}
        )
        return reaction


class PostReactionsSerializer(serializers.ModelSerializer):
    count = serializers.IntegerField(read_only=True, default=0)
    my_reaction = serializers.SerializerMethodField()

    class Meta:
        model = ReactionType
        fields = [
            "id",  # Include ID so frontend can identify reactions
            "name",
            "emoji",
            "count",
            "my_reaction",
        ]

    def get_my_reaction(self, obj: ReactionType):
        # Get user_reactions from context (prefetched once to avoid N+1)
        user_reactions = self.context.get("user_reactions", set())
        return obj.id in user_reactions
