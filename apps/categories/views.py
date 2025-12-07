import logging

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.categories.models import Category
from apps.categories.serializers import CategorySerializer
from apps.common.pagination import PostPageNumberPagination
from apps.common.permissions.base import IsAdmin
from apps.posts.serializers import PostListSerializer

logger = logging.getLogger(__name__)


@extend_schema(tags=["Categories"])
class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update"]:
            return [IsAdmin()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.action == "posts":
            return PostListSerializer
        return CategorySerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        logger.info(
            "[CATEGORY] Category created - category_id=%s, name=%s", instance.pk, instance.name
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        logger.info(
            "[CATEGORY] Category updated - category_id=%s, name=%s", instance.pk, instance.name
        )

    def perform_destroy(self, instance):
        category_id = instance.pk
        category_name = instance.name
        instance.delete()
        logger.info(
            "[CATEGORY] Category deleted - category_id=%s, name=%s", category_id, category_name
        )

    @action(methods=["get"], detail=True, url_path="posts")
    def posts(self, request, pk=None):
        category: Category = self.get_object()
        qs = category.posts.all().select_related("author", "category").prefetch_related("images")
        paginator = PostPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
