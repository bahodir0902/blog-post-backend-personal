import logging

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.users.auth.otp import create_scoped_otp
from apps.users.models import User
from apps.users.service import send_email_to_verify_email

logger = logging.getLogger(__name__)
EMAIL_SCOPE = "email_change"


class RequestEmailChangeSerializer(serializers.Serializer):
    user_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    new_email = serializers.EmailField()

    def validate(self, attrs):
        new_email = attrs.get("new_email")
        if User.objects.filter(email=new_email).exists():
            raise ValidationError(f"User with {new_email} email already exists.")
        return attrs

    def create(self, validated_data):
        user = None
        user_id = validated_data.get("user_id")
        if user_id:
            user = User.objects.filter(pk=user_id).first()
        if not user and self.context.get("request"):
            user = self.context["request"].user
        if not user:
            raise ValidationError("User not found")

        new_email = validated_data["new_email"]
        otp_token, code = create_scoped_otp(
            scope=EMAIL_SCOPE, uid=user.pk, meta={"new_email": new_email}
        )
        send_email_to_verify_email(new_email, getattr(user, "first_name", None), code)

        return {
            "message": f"Successfully sent verification code to {new_email}",
            "otp_token": otp_token,
        }
