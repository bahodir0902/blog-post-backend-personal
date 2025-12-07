from django.db import models

from apps.users.models import User

from .comments import Comment


class CommentReaction(models.Model):
    class CommentReactionType(models.TextChoices):
        LIKE = "LIKE", "Like"
        DISLIKE = "DISLIKE", "Dislike"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comment_reactions")
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="reactions")
    reaction = models.CharField(max_length=30, choices=CommentReactionType.choices)

    class Meta:
        db_table = "Comment_reactions"
        verbose_name = "Comment Reaction"
        verbose_name_plural = "Comment Reactions"
        unique_together = ("user", "comment")

    def __str__(self):
        return f"{self.user} -> {self.comment_id} : {self.reaction}"
