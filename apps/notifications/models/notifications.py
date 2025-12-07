from django.db import models

from apps.common.models import BaseModel


class CommentNotification(BaseModel):
    receiver = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="received_notifications"
    )
    sender = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="sent_notifications"
    )
    comment = models.ForeignKey(
        "comments.Comment", on_delete=models.CASCADE, related_name="notifications"
    )
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)

    class Meta:
        db_table = "CommentNotifications"
        verbose_name = "Comment Notification"
        verbose_name_plural = "Comment Notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification to {self.receiver} from {self.sender}"
