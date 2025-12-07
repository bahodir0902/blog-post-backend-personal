from django.db import models

from apps.common.models import BaseModel
from apps.posts.models import Post
from apps.users.models import User


class Favourite(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favourites")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="favourited_by")

    def __str__(self):
        return f"Favourite by '{self.user.email}' to '{self.post.title}' post"

    class Meta:
        db_table = "Favourites"
        verbose_name = "Favourite"
        verbose_name_plural = "Favourites"
        unique_together = ("user", "post")
