import logging

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.common.permissions.base import IsAuthorOrAdmin
from apps.posts.models import Post, PostImage, ReactionType
from apps.posts.serializers import (
    PostDetailSerializer,
    PostListSerializer,
    PostWriteSerializer,
    ReactionTypeSerializer,
)

logger = logging.getLogger(__name__)


@extend_schema(tags=["Posts"])
class AuthorPostViewSet(ModelViewSet):
    permission_classes = [IsAuthorOrAdmin]
    lookup_field = "slug"

    def get_queryset(self):
        qs = (
            Post.objects.all()
            .select_related("author", "category")
            .prefetch_related("images", "allowed_reactions", "tags")
        )
        user = self.request.user
        return qs if user.is_superuser else qs.filter(author=user)

    def get_serializer_class(self):
        if self.action in ["retrieve"]:
            return PostDetailSerializer
        if self.action in ["create", "update", "partial_update"]:
            return PostWriteSerializer
        elif self.action == "list_available_reactions":
            return ReactionTypeSerializer
        return PostListSerializer

    def perform_create(self, serializer):
        instance = serializer.save(author=self.request.user)
        logger.info(
            "[POST] Post created - post_id=%s, slug=%s, author_id=%s",
            instance.pk,
            instance.slug,
            self.request.user.pk,
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        logger.info(
            "[POST] Post updated - post_id=%s, slug=%s, author_id=%s",
            instance.pk,
            instance.slug,
            self.request.user.pk,
        )

    def perform_destroy(self, instance):
        post_id = instance.pk
        post_slug = instance.slug
        author_id = instance.author.pk
        instance.delete()
        logger.info(
            "[POST] Post deleted - post_id=%s, slug=%s, author_id=%s",
            post_id,
            post_slug,
            author_id,
        )

    @action(methods=["post"], detail=True, url_path="images", parser_classes=[MultiPartParser])
    def upload_image(self, request, slug=None):
        post = self.get_object()
        file = request.FILES.get("image")
        if not file:
            return Response({"detail": "No image provided."}, status=400)
        img = PostImage.objects.create(post=post, image=file)
        url = request.build_absolute_uri(img.image.url)  # << absolute URL
        logger.info(
            "[POST] Post image uploaded - post_id=%s, slug=%s, image_id=%s, author_id=%s",
            post.pk,
            post.slug,
            img.pk,
            request.user.pk,
        )
        return Response({"id": img.pk, "url": url}, status=201)

    @action(methods=["get"], detail=False, url_path="my-posts")
    def my_posts(self, request):
        qs = self.get_queryset().filter(author=request.user)
        page = self.paginate_queryset(qs)
        ser = PostListSerializer(page or qs, many=True)
        return self.get_paginated_response(ser.data) if page is not None else Response(ser.data)

    @action(
        methods=["post"],
        detail=False,
        url_path="upload-temp-image",
        parser_classes=[MultiPartParser],
    )
    def upload_temp_image(self, request):
        """
        Accept an image upload before a Post exists.
        Creates PostImage with post=None and returns {id, url}.
        """
        file = request.FILES.get("image")
        if not file:
            return Response({"detail": "No image provided."}, status=400)
        img = PostImage.objects.create(post=None, image=file)
        url = request.build_absolute_uri(img.image.url)  # << absolute URL
        return Response({"id": img.pk, "url": url}, status=201)

    @action(methods=["post"], detail=True, url_path="adopt-images")
    def adopt_images(self, request, slug=None):
        """
        Attach previously uploaded PostImage records to this Post.
        Body: { "image_ids": [1,2,3] }
        """
        post = self.get_object()
        ids = request.data.get("image_ids") or []
        if not isinstance(ids, list):
            return Response({"detail": "image_ids must be a list."}, status=400)

        updated = PostImage.objects.filter(id__in=ids, post__isnull=True).update(post=post)
        logger.info(
            "[POST] Post images adopted - post_id=%s, slug=%s, images_count=%s, author_id=%s",
            post.pk,
            post.slug,
            updated,
            request.user.pk,
        )
        return Response({"attached": updated}, status=200)

    @action(methods=["get"], detail=False, url_path="list-available-reactions")
    def list_available_reactions(self, request):
        qs = ReactionType.objects.all()
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
