from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q

from apps.common.utils.files import unique_image_path
from apps.common.utils.validators import validate_image_size
from core.storages import PublicMediaStorage


class UserProfile(models.Model):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="profile")
    middle_name = models.CharField(max_length=120, null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    profile_photo = models.ImageField(
        storage=PublicMediaStorage(),
        null=True,
        blank=True,
        upload_to=unique_image_path,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"]),
            validate_image_size,
        ],
    )

    def __str__(self):
        return f"profile for {self.user.first_name} - {self.user.last_name} - {self.user.email}"

    class Meta:
        db_table = "Users Profile"
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        constraints = [
            models.UniqueConstraint(
                fields=["phone_number"],
                name="unique_phone_number_when_set",
                condition=~Q(phone_number=None),
            )
        ]
