from django.db import models

from apps.common.models import BaseModel
from apps.posts.models import Post
from apps.users.models import User


class Bookmark(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookmarks")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="bookmarked_by")

    def __str__(self):
        return f"Bookmark by '{self.user.email}' to '{self.post.title}' name"

    class Meta:
        db_table = "Bookmarks"
        verbose_name = "Bookmark"
        verbose_name_plural = "Bookmarks"
        unique_together = ("user", "post")
