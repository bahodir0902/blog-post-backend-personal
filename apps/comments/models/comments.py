from django.db import models, transaction

from apps.common.models import BaseModel
from apps.posts.models import Post
from apps.users.models import User

from .comment_manager import CommentsManager


class Comment(BaseModel):
    post = models.ForeignKey(
        Post, on_delete=models.SET_NULL, null=True, related_name="comments", db_index=True
    )
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="comments", db_index=True
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="replies",
        null=True,
        blank=True,
        db_index=True,
    )
    content = models.TextField()

    is_edited = models.BooleanField(default=False)

    objects = CommentsManager()

    class Meta:
        db_table = "Comments"
        verbose_name = "Comment"
        verbose_name_plural = "Comments"

    def delete(self, using=None, keep_parents=False):
        self.soft_delete()

    def soft_delete(self):
        with transaction.atomic():
            self.is_deleted = True
            self.save(update_fields=["is_deleted"])

        for child in self.replies.all():
            child.soft_delete()

    def __str__(self):
        return f"{self.pk}. Comment by {self.author} on {self.post}"


class CommentEditHistory(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="edit_history")
    previous_content = models.TextField()
    edited_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "CommentEditHistory"
        verbose_name = "Edited Comment History"
        verbose_name_plural = "Edited Comment Histories"

    def __str__(self):
        return f"Edited Comment on {self.comment} at {self.edited_at}"
