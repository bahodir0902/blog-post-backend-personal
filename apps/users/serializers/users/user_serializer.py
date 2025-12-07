from rest_framework import serializers

from apps.users.models import User


class UserSerializer(serializers.ModelSerializer):
    groups = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "mfa_enabled",
            "date_joined",
            "last_login",
            "role",
            "groups",
            "status",
        ]
        extra_kwargs = {"role": {"required": False}}

    def get_groups(self, obj: User):
        return obj.groups.values_list("name", flat=True)

    def get_status(self, obj: User) -> str:
        if obj.is_active and not obj.must_set_password and obj.email_verified:
            return "Authorized"
        elif obj.is_active and (obj.must_set_password or not obj.email_verified):
            return "Unauthorized"
        return "Deactivated"
