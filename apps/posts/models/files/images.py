from django.db import models

from apps.common.models import BaseModel
from apps.common.utils.files import unique_image_path
from apps.posts.models import Post
from core.storages import PublicMediaStorage


class PostImage(BaseModel):
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="images", null=True, blank=True
    )
    image = models.ImageField(storage=PublicMediaStorage(), upload_to=unique_image_path)
    alt_text = models.CharField(max_length=255, blank=True)
    caption = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)

    original_name = models.CharField(max_length=255, null=True, blank=True)
    size = models.PositiveIntegerField(null=True, blank=True)
    content_type = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        ordering = ["sort_order", "id"]
        db_table = "PostImages"
        verbose_name = "Post Image"
        verbose_name_plural = "Post Images"

    def __str__(self):
        return f"Image #{self.pk} for {self.post or 'unassigned'}"

    def save(self, *args, **kwargs):
        if self.image:
            self.original_name = self.image.name.split("/")[-1]
            self.size = self.image.size
            self.content_type = getattr(self.image.file, "content_type", None)
        super().save(*args, **kwargs)
