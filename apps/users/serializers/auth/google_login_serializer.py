import logging

from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User, UserProfile

logger = logging.getLogger(__name__)


class GoogleLoginSerializer(serializers.Serializer):
    credential = serializers.CharField(required=True)

    def validate_credential(self, value):
        try:
            client_id = settings.GOOGLE_OAUTH_CLIENT_ID
            idinfo = id_token.verify_oauth2_token(value, google_requests.Request(), client_id)
            return idinfo
        except ValueError:
            raise serializers.ValidationError("Invalid Google token")
        except Exception as e:
            logger.error(
                "[GOOGLE_AUTH] Unexpected error during token validation - error=%s",
                str(e),
                exc_info=True,
            )
            raise serializers.ValidationError("Authentication failed")

    def create(self, validated_data):
        idinfo = validated_data["credential"]
        email = idinfo.get("email")
        if not email:
            logger.error("[GOOGLE_AUTH] No email in token payload")
            raise serializers.ValidationError("Email not provided by Google")

        email_verified = idinfo.get("email_verified", False)
        google_id = idinfo.get("sub")
        first_name = idinfo.get("given_name", "")
        last_name = idinfo.get("family_name", "")
        # picture = idinfo.get("picture", "")

        user = None
        if google_id:
            user = User.objects.filter(google_id=google_id).first()

        if not user:
            user = User.objects.filter(email=email).first()

        created = False
        if not user:
            # Create new user
            user = User.objects.create(
                email=email,
                google_id=google_id,
                first_name=first_name,
                last_name=last_name,
                email_verified=email_verified,
                must_set_password=False,
            )
            user.set_unusable_password()
            user.save()

            # Create user profile
            UserProfile.objects.create(user=user)

            created = True
            logger.info(
                "[GOOGLE_AUTH] New user created via Google - user_id=%s, email=%s", user.pk, email
            )
        else:
            # Update existing user
            updated = False
            if not user.google_id and google_id:
                user.google_id = google_id
                updated = True

            if email_verified and not user.email_verified:
                user.email_verified = email_verified
                updated = True

            if not user.first_name and first_name:
                user.first_name = first_name
                updated = True

            if not user.last_name and last_name:
                user.last_name = last_name
                updated = True

            if updated:
                user.save()

            logger.info(
                "[GOOGLE_AUTH] Existing user logged in via Google - user_id=%s, email=%s",
                user.pk,
                email,
            )

        # Check if user is active
        if not user.is_active:
            logger.warning("[GOOGLE_AUTH] Inactive user attempted login - user_id=%s", user.pk)
            raise serializers.ValidationError("Account is deactivated")

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email_verified": user.email_verified,
            },
            "created": created,
        }
