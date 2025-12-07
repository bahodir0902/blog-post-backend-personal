from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import connection
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.comments.models import Comment
from apps.notifications.models import CommentNotification
from apps.notifications.serializers import CommentNotificationReadSerializer


@receiver(post_save, dispatch_uid="send_comment_notification_unique", sender=Comment)
def send_comment_notification(sender, instance: Comment, created, **kwargs):
    if not created:
        return
    parent = instance.parent

    if not parent:
        return

    if instance.author_id == parent.author_id:
        return

    sender_fill_name = (
        f"{instance.author.first_name} {instance.author.last_name}".strip()
        if instance.author
        else "Someone"
    )

    obj = CommentNotification.objects.create(
        sender=instance.author,
        receiver=instance.parent.author,
        comment=instance,
        message=f"{sender_fill_name} replied to you in "
        f"{instance.post.title if instance.post else 'a post'}",
    )
    with connection.cursor() as cursor:
        cursor.execute(
            """
                       SELECT COUNT(*)
                       FROM "CommentNotifications"
                       WHERE receiver_id = %s
                         AND is_read = FALSE
                       """,
            [instance.parent.author_id],
        )
        current = cursor.fetchone()[0]

    unread_count = current + 1
    ctx = {"unread_count": unread_count}

    payload = CommentNotificationReadSerializer(obj, context=ctx).data
    send_realtime_notification(obj.receiver_id, payload)


def send_realtime_notification(receiver_id, payload):
    channel_layer = get_channel_layer()
    group_name = f"comment_notification_room_id_{receiver_id}"
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "comment_notification",
            "payload": payload,
        },
    )
