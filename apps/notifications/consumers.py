import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from apps.notifications.models import CommentNotification

logger = logging.getLogger(__name__)


class CommentNotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user or not getattr(self.user, "is_authenticated", False):
            await self.close()
            return

        self.comment_notification_room_id = str(self.user.pk)
        self.room_group_name = f"comment_notification_room_id_{self.comment_notification_room_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        """Handle messages coming from the WebSocket client."""
        if text_data is None:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
            return

        message_type = data.get("type")
        payload = data.get("payload", {})

        if message_type == "comment_notification":
            await self.send_error("Clients should not send 'comment_notification' messages.")
            return

        if message_type == "mark_as_read":
            # payload: {"ids": [1,2,3]} or {"id": 1}
            ids = payload.get("ids") or ([payload.get("id")] if payload.get("id") else [])
            if not ids:
                await self.send_error("No notification id(s) provided for mark_as_read.")
                return
            try:
                updated = await self.mark_as_read_bulk(ids)
                await self.send(
                    json.dumps({"type": "mark_as_read_result", "payload": {"updated": updated}})
                )
            except Exception as e:
                logger.exception(f"[WEBSOCKET] Failed to mark notifications as read: {e}")
                await self.send_error("Failed to mark notifications as read.")
            return

        await self.send_error("Unknown message type.")

    async def send_error(self, error_message):
        await self.send(text_data=json.dumps({"type": "error", "message": error_message}))

    async def comment_notification(self, event):
        """
        {
            'type': 'comment_notification',
            'payload': {... serialized notification ...}
        }
        """
        payload = event.get("payload", {})
        if not payload:
            return

        await self.send(text_data=json.dumps({"type": "comment_notification", "payload": payload}))

    @database_sync_to_async
    def mark_as_read_bulk(self, ids):
        """
        Only allow the authenticated receiver to mark their own notifications.
        Return number of updated rows.
        """
        qs = CommentNotification.objects.filter(id__in=ids, receiver_id=self.user.pk, is_read=False)
        updated = qs.update(is_read=True)
        return updated

    @database_sync_to_async
    def delete_notifications_bulk(self, ids):
        """
        Only allow the authenticated receiver to delete their own notifications.
        Return number of deleted rows.
        """
        qs = CommentNotification.objects.filter(id__in=ids, receiver_id=self.user.pk)
        deleted_count, _ = qs.delete()
        return deleted_count
