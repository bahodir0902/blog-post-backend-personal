from django.db import models

from apps.common.models import BaseModel


class Tag(BaseModel):
    name = models.CharField(unique=True, max_length=100)
    slug = models.SlugField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "Tags"
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["slug"]),
        ]
