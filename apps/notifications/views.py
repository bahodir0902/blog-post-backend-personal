import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.comments.pagination import CommentPageNumberPagination

from .models import CommentNotification
from .serializers import (
    CommentNotificationReadSerializer,
    DeleteCommentNotificationSerializer,
    MarkAsReadSerializer,
)

logger = logging.getLogger(__name__)


@extend_schema(tags=["CommentNotifications"])
class CommentNotificationViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = CommentPageNumberPagination

    def get_queryset(self):
        base_qs = CommentNotification.objects.all().select_related(
            "sender", "receiver", "comment__post"
        )

        return base_qs

    def get_serializer_class(self):
        if self.action == "inbox":
            return CommentNotificationReadSerializer
        elif self.action == "delete_notifications":
            return DeleteCommentNotificationSerializer
        return MarkAsReadSerializer

    def paginate_queryset(self, queryset):
        if self.action == "inbox":
            return super().paginate_queryset(queryset)
        return None

    @action(methods=["get"], detail=False)
    def inbox(self, request):
        qs = self.get_queryset().filter(receiver=request.user).order_by("-created_at")

        unread_count = CommentNotification.objects.filter(
            receiver=request.user, is_read=False
        ).count()
        ctx = {"unread_count": unread_count}

        paginated = self.paginate_queryset(qs)
        if paginated is not None:
            ser = self.get_serializer(paginated, many=True, context=ctx)
            return self.get_paginated_response(ser.data)

        ser = self.get_serializer(qs, many=True, context=ctx)
        return Response(ser.data)

    @action(methods=["post"], detail=False, url_path="mark-as-read")
    def mark_as_read(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        updated_count = ser.save()
        logger.info(
            "[NOTIFICATION] Notifications marked as read - user_id=%s, count=%s",
            request.user.pk,
            updated_count,
        )
        return Response({"message": "success"})

    @action(methods=["post"], detail=False, url_path="delete-notifications")
    def delete_notifications(self, request):
        """
        Delete notifications by IDs. Only the receiver can delete their own notifications.
        """
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        deleted_count = ser.save()
        logger.info(
            "[NOTIFICATION] Notifications deleted - user_id=%s, count=%s",
            request.user.pk,
            deleted_count,
        )
        return Response(
            {"message": "success", "deleted_count": deleted_count}, status=status.HTTP_200_OK
        )
