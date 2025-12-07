import logging

from django.core.exceptions import BadRequest
from django.db.models import Count, OuterRef, Prefetch, Q, Subquery
from django.db.models.functions import Coalesce
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.comments.models import Comment, CommentEditHistory, CommentReaction
from apps.comments.pagination import CommentPageNumberPagination
from apps.comments.serializers import CommentCreateSerializer, CommentReadSerializer
from apps.posts.models import Post

logger = logging.getLogger(__name__)


@extend_schema(tags=["Posts"])
class CommentViewSet(ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = CommentPageNumberPagination
    filter_backends = [OrderingFilter]
    ordering = ["-created_at"]
    ordering_fields = ["likes", "dislikes", "created_at", "-created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return CommentCreateSerializer
        return CommentReadSerializer

    def get_queryset(self):
        post_slug = self.kwargs.get("post_slug")
        post: Post = Post.objects.filter(slug=post_slug).first()
        if not post or not post.allow_comments:
            return Comment.objects.none()

        reply_count_subquery = (
            Comment.objects.filter(parent=OuterRef("pk"))
            .values("parent")
            .annotate(count=Count("id"))
            .values("count")
        )

        likes_subquery = (
            CommentReaction.objects.filter(
                comment=OuterRef("pk"),
                reaction=CommentReaction.CommentReactionType.LIKE,
            )
            .values("comment")
            .annotate(count=Count("id"))
            .values("count")
        )

        dislikes_subquery = (
            CommentReaction.objects.filter(
                comment=OuterRef("pk"),
                reaction=CommentReaction.CommentReactionType.DISLIKE,
            )
            .values("comment")
            .annotate(count=Count("id"))
            .values("count")
        )

        base_qs = (
            Comment.objects.filter(post__slug=post_slug)
            .select_related("author")
            .prefetch_related("replies")
            .annotate(
                reply_count=Coalesce(Subquery(reply_count_subquery), 0),
                likes=Coalesce(Subquery(likes_subquery), 0),
                dislikes=Coalesce(Subquery(dislikes_subquery), 0),
            )
        )

        if self.action == "list":
            qs = base_qs.filter(parent__isnull=True)
        else:
            qs = base_qs

        request = getattr(self, "request", None)
        if request and request.user.is_authenticated:
            user_reactions_qs = CommentReaction.objects.filter(user=request.user)
            qs = qs.prefetch_related(
                Prefetch("reactions", queryset=user_reactions_qs, to_attr="user_reactions")
            )

        return qs

    def _get_comment_or_400(self, pk=None):
        pk = pk or self.kwargs.get("pk")
        try:
            return Comment.objects.get(pk=pk)
        except Comment.DoesNotExist:
            raise BadRequest("Invalid comment id.")

    def _handle_reaction(self, comment, reaction_type):
        reaction, created = CommentReaction.objects.get_or_create(
            user=self.request.user,
            comment=comment,
            defaults={"reaction": reaction_type},
        )

        if not created:
            if reaction.reaction == reaction_type:
                reaction.delete()
                logger.info(
                    "[COMMENT] Comment reaction removed - comment_id=%s, reaction_type=%s,"
                    " user_id=%s",
                    comment.pk,
                    reaction_type,
                    self.request.user.pk,
                )
            else:
                reaction.reaction = reaction_type
                reaction.save(update_fields=["reaction"])
                logger.info(
                    "[COMMENT] Comment reaction updated - comment_id=%s, reaction_type=%s,"
                    " user_id=%s",
                    comment.pk,
                    reaction_type,
                    self.request.user.pk,
                )
        else:
            logger.info(
                "[COMMENT] Comment reaction added - comment_id=%s, reaction_type=%s," " user_id=%s",
                comment.pk,
                reaction_type,
                self.request.user.pk,
            )

        return Response({"success": True})

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        post_slug = self.kwargs.get("post_slug")
        response.data["total_comments"] = Comment.objects.filter(post__slug=post_slug).count()
        return response

    def perform_create(self, serializer):
        post_slug = self.kwargs.get("post_slug")
        post = Post.objects.filter(slug=post_slug).first()
        instance = serializer.save(author=self.request.user, post=post)
        logger.info(
            "[COMMENT] Comment created - comment_id=%s, post_slug=%s, user_id=%s",
            instance.pk,
            post_slug,
            self.request.user.pk,
        )

    def partial_update(self, request, *args, **kwargs):
        comment = self.get_object()

        if comment.author != request.user and not request.user.is_staff:
            raise PermissionDenied("You cannot edit this comment.")

        CommentEditHistory.objects.create(
            comment=comment,
            previous_content=comment.content,
        )

        comment.content = request.data.get("content", comment.content)
        comment.is_edited = True
        comment.save(update_fields=["content", "is_edited", "updated_at"])

        logger.info(
            "[COMMENT] Comment updated - comment_id=%s, user_id=%s",
            comment.pk,
            request.user.pk,
        )

        return Response(self.get_serializer(comment).data)

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        if comment.author != request.user and not request.user.is_staff:
            raise PermissionDenied("You cannot delete this comment.")

        comment_id = comment.pk
        comment.soft_delete()
        logger.info(
            "[COMMENT] Comment deleted - comment_id=%s, user_id=%s",
            comment_id,
            request.user.pk,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=["get"], detail=True, url_path="view-replies")
    def view_replies(self, request, *args, **kwargs):
        parent_comment = self.get_object()

        qs = (
            Comment.objects.filter(parent=parent_comment)
            .select_related("author")
            .annotate(
                likes=Count(
                    "reactions",
                    filter=Q(reactions__reaction=CommentReaction.CommentReactionType.LIKE),
                    distinct=True,
                ),
                dislikes=Count(
                    "reactions",
                    filter=Q(reactions__reaction=CommentReaction.CommentReactionType.DISLIKE),
                    distinct=True,
                ),
            )
        )

        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            user_reactions_qs = CommentReaction.objects.filter(user=user)
            qs = qs.prefetch_related(
                Prefetch("reactions", queryset=user_reactions_qs, to_attr="user_reactions")
            )

        serializer = self.get_serializer(qs, many=True, context=self.get_serializer_context())

        return Response(serializer.data)

    @action(methods=["post"], detail=True, url_path="like")
    def like(self, request, *args, **kwargs):
        comment = self._get_comment_or_400()
        return self._handle_reaction(comment, CommentReaction.CommentReactionType.LIKE)

    @action(methods=["post"], detail=True, url_path="dislike")
    def dislike(self, request, *args, **kwargs):
        comment = self._get_comment_or_400()
        return self._handle_reaction(comment, CommentReaction.CommentReactionType.DISLIKE)
