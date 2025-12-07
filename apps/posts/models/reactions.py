from django.db import models

from apps.common.models import BaseModel
from apps.users.models import User


class ReactionType(BaseModel):
    name = models.CharField(max_length=100)
    emoji = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.name} -> {self.emoji} emoji"

    class Meta:
        db_table = "ReactionTypes"
        verbose_name = "Reaction Type"
        verbose_name_plural = "Reaction Types"


class Reaction(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reacted_posts")
    post = models.ForeignKey("posts.Post", on_delete=models.CASCADE, related_name="reacted_by")
    type = models.ForeignKey(ReactionType, on_delete=models.CASCADE, related_name="reactions")

    def __str__(self):
        return f"{self.user.email} -> {self.post.title} -> {self.type.name}"

    class Meta:
        db_table = "Reactions"
        verbose_name = "Reaction"
        verbose_name_plural = "Reactions"
        unique_together = ("user", "post")
