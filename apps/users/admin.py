from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.html import format_html
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django import forms

from unfold.admin import ModelAdmin, StackedInline
from unfold.decorators import action

from .models.user import User, Role
from .models.profile import UserProfile
from .service import send_activation_invite


class UserProfileInline(StackedInline):
    model = UserProfile
    can_delete = False
    fields = (
        "profile_preview",
        "profile_photo",
        "middle_name",
        "birth_date",
        "phone_number",
        "updated_at",
    )
    readonly_fields = ("profile_preview", "updated_at")

    def profile_preview(self, obj):
        if obj and obj.profile_photo:
            return format_html(
                '<img src="{}" style="width: 150px; height: 150px; object-fit: cover; '
                'border-radius: 50%; box-shadow: 0 4px 6px rgba(0,0,0,0.1);" />',
                obj.profile_photo.url
            )
        return format_html(
            '<div style="width: 150px; height: 150px; background: #e5e7eb; border-radius: 50%; '
            'display: flex; align-items: center; justify-content: center; color: #9ca3af; '
            'font-size: 48px;">👤</div>'
        )

    profile_preview.short_description = "Current Profile Photo"


class UserAdminForm(forms.ModelForm):
    let_user_set_password = forms.BooleanField(
        label=_("Let user set password"),
        required=False,
        initial=True,
        help_text=_(
            "If checked, an invitation link will be sent to the user. "
            "If unchecked, you can set a password manually."
        ),
        widget=forms.CheckboxInput(
            attrs={
                "class": "user-password-toggle user-password-toggle--fancy",
                "data-toggle": "password-invite",
            }
        ),
    )

    raw_password = forms.CharField(
        label=_("Set password"),
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "vTextField password-field",
                "placeholder": _("Enter password for the user"),
                "autocomplete": "new-password",
            }
        ),
        help_text=_("Enter a raw password. Django will automatically hash it before saving."),
    )

    class Meta:
        model = User
        fields = "__all__"
        # We don't want the built-in password field in the admin form,
        # we handle it via raw_password / let_user_set_password
        exclude = ("password",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # For existing users: hide the password controls (only for creation)
        if self.instance.pk:
            self.fields["let_user_set_password"].widget = forms.HiddenInput()
            self.fields["raw_password"].widget = forms.HiddenInput()
            self.fields["let_user_set_password"].required = False
            self.fields["raw_password"].required = False

    def clean(self):
        cleaned_data = super().clean()

        # Only enforce logic for new users
        if not self.instance.pk:
            let_user_set = cleaned_data.get("let_user_set_password", True)
            raw_password = cleaned_data.get("raw_password")

            if not let_user_set and not raw_password:
                raise ValidationError(
                    {
                        "raw_password": _(
                            "Please enter a password or check 'Let user set password'."
                        )
                    }
                )

            if let_user_set and raw_password:
                raise ValidationError(
                    _(
                        "You cannot set both 'Let user set password' and provide a manual password. "
                        "Please choose one option."
                    )
                )

        return cleaned_data

    def save(self, commit=True):
        user: User = super().save(commit=False)

        is_new_user = not self.instance.pk

        if is_new_user:
            let_user_set = self.cleaned_data.get("let_user_set_password", True)
            raw_password = self.cleaned_data.get("raw_password")

            if let_user_set:
                # User will set password via invite link
                user.set_unusable_password()
                user.save()

                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                send_activation_invite(user.email, user.first_name, uid, token)
            else:
                # Admin sets password directly
                user.password = make_password(raw_password)
                user.must_set_password = False
                user.email_verified = True
                user.save()

        if commit:
            if not is_new_user:
                user.save()
            self.save_m2m()

        return user


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserAdminForm
    add_form = UserAdminForm  # This is the key addition to fix the FieldError

    # Unfold configuration
    compressed_fields = True
    warn_unsaved_form = True

    list_display = [
        "user_card",
        "email_with_verification",
        "role_badge",
        "status_indicators",
        "posts_count",
        "last_login_display",
        "date_joined_display",
    ]

    list_filter = [
        "role",
        "is_active",
        "is_staff",
        "is_superuser",
        "email_verified",
        "mfa_enabled",
        "must_set_password",
        "date_joined",
        "last_login",
        "groups",
    ]

    list_filter_submit = True

    search_fields = ["email", "first_name", "last_name", "google_id"]

    readonly_fields = [
        "date_joined",
        "last_login",
        "google_id",
        "user_stats",
    ]

    fieldsets = (
        ("👤 Personal Information", {
            "fields": ("first_name", "last_name", "email"),
            "description": "Basic user information"
        }),
        (_("Password Settings"), {
            "fields": ("let_user_set_password", "raw_password"),
            "classes": ("password-settings",),
            "description": format_html(
                '<div class="password-info">'
                '<strong>⚠️ Password Configuration (New Users Only)</strong><br>'
                '• <strong>Let user set password (checked):</strong> '
                'User will receive an invitation email to set their own password.<br>'
                '• <strong>Let user set password (unchecked):</strong> '
                'You can set a password manually below. Django will hash it automatically.'
                "</div>"
            ),
        }),
        ("🔐 Authentication", {
            "fields": (
                "google_id",
                "email_verified",
                "must_set_password",
                "mfa_enabled",
            ),
        }),
        ("👔 Role & Permissions", {
            "fields": ("role", "is_active", "is_staff", "is_superuser", "groups",
                       "user_permissions"),
        }),
        ("📊 Statistics", {
            "fields": ("user_stats",),
        }),
        ("🗑️ Account Status", {
            "fields": ("is_deleted",),
        }),
        ("📅 Important Dates", {
            "fields": ("date_joined", "last_login"),
            "classes": ["collapse"],
        }),
    )

    add_fieldsets = (
        ("Create New User", {
            "classes": ["wide"],
            "fields": ("email", "first_name", "last_name", "let_user_set_password", "raw_password",
                       "role"),
        }),
    )

    inlines = [UserProfileInline]

    filter_horizontal = ["groups", "user_permissions"]

    list_per_page = 25

    actions = [
        "verify_emails",
        "enable_mfa",
        "disable_mfa",
        "make_author",
        "make_admin",
        "deactivate_users",
        "activate_users",
    ]

    ordering = ["-date_joined"]

    # Custom display methods
    def user_card(self, obj):
        full_name = f"{obj.first_name} {obj.last_name or ''}".strip()
        if not full_name:
            full_name = obj.email.split('@')[0]

        if hasattr(obj, 'profile') and obj.profile.profile_photo:
            return format_html(
                '<div style="display: flex; align-items: center; gap: 10px;">'
                '<img src="{}" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover;" />'
                '<div><strong>{}</strong><br/><small style="color: #9ca3af;">ID: {}</small></div>'
                '</div>',
                obj.profile.profile_photo.url,
                full_name,
                obj.id
            )
        else:
            return format_html(
                '<div style="display: flex; align-items: center; gap: 10px;">'
                '<div style="width: 32px; height: 32px; border-radius: 50%; background: #e5e7eb; display: flex; align-items: center; justify-content: center;">👤</div>'
                '<div><strong>{}</strong><br/><small style="color: #9ca3af;">ID: {}</small></div>'
                '</div>',
                full_name,
                obj.id
            )

    user_card.short_description = "User"
    user_card.admin_order_field = "first_name"

    def email_with_verification(self, obj):
        email_html = f'<div>{obj.email}'

        if obj.email_verified:
            email_html += ' <span style="color: #10b981;" title="Verified">✓</span>'
        else:
            email_html += ' <span style="color: #ef4444;" title="Not verified">⚠️</span>'

        if obj.google_id:
            email_html += ' <span style="background: #4285f4; color: white; padding: 2px 6px; border-radius: 4px; font-size: 9px;">G</span>'

        email_html += '</div>'
        return format_html(email_html)

    email_with_verification.short_description = "Email"
    email_with_verification.admin_order_field = "email"

    def role_badge(self, obj):
        role_config = {
            Role.ADMIN: {"color": "#dc2626", "icon": "👑", "bg": "#fee2e2"},
            Role.AUTHOR: {"color": "#2563eb", "icon": "✍️", "bg": "#dbeafe"},
            Role.USER: {"color": "#6b7280", "icon": "👤", "bg": "#f3f4f6"},
        }

        config = role_config.get(obj.role, role_config[Role.USER])

        html = f'<span style="background: {config["bg"]}; color: {config["color"]}; padding: 6px 12px; border-radius: 6px; font-weight: 600; font-size: 11px; display: inline-block;">{config["icon"]} {obj.get_role_display()}</span>'

        if obj.is_superuser:
            html += ' <span style="background: #7c3aed; color: white; padding: 4px 8px; border-radius: 4px; font-size: 9px;">⚡ SUPER</span>'

        if obj.is_staff:
            html += ' <span style="background: #059669; color: white; padding: 4px 8px; border-radius: 4px; font-size: 9px;">STAFF</span>'

        return format_html(html)

    role_badge.short_description = "Role"
    role_badge.admin_order_field = "role"

    def status_indicators(self, obj):
        html = ""

        if obj.is_active:
            html += '<span style="color: #10b981; font-size: 11px;" title="Active">● Active</span>'
        else:
            html += '<span style="color: #ef4444; font-size: 11px;" title="Inactive">● Inactive</span>'

        if obj.mfa_enabled:
            html += ' <span style="background: #dbeafe; color: #1e40af; padding: 2px 6px; border-radius: 4px; font-size: 9px;">🔒 MFA</span>'

        if obj.must_set_password:
            html += ' <span style="background: #fef3c7; color: #92400e; padding: 2px 6px; border-radius: 4px; font-size: 9px;">⚠️ PWD</span>'

        if obj.is_deleted:
            html += ' <span style="background: #fee2e2; color: #991b1b; padding: 2px 6px; border-radius: 4px; font-size: 9px;">🗑️ DEL</span>'

        return format_html(html)

    status_indicators.short_description = "Status"

    def posts_count(self, obj):
        count = obj.posts.count()
        if count > 0:
            return format_html(
                '<a href="/admin/posts/post/?author__id__exact={}">'
                '<span style="background: #dbeafe; color: #1e40af; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 600;">📝 {}</span>'
                '</a>',
                obj.id,
                count
            )
        return format_html('<span style="color: #9ca3af; font-size: 11px;">No posts</span>')

    posts_count.short_description = "Posts"

    def last_login_display(self, obj):
        if obj.last_login:
            delta = now() - obj.last_login
            if delta.days == 0:
                return "Today"
            elif delta.days == 1:
                return "Yesterday"
            elif delta.days < 7:
                return f"{delta.days}d ago"
            elif delta.days < 30:
                return f"{delta.days // 7}w ago"
            else:
                return f"{delta.days // 30}mo ago"
        return "Never"

    last_login_display.short_description = "Last Login"
    last_login_display.admin_order_field = "last_login"

    def date_joined_display(self, obj):
        return obj.date_joined.strftime("%b %d, %Y")

    date_joined_display.short_description = "Joined"
    date_joined_display.admin_order_field = "date_joined"

    def user_stats(self, obj):
        total_posts = obj.posts.count()
        published_posts = obj.posts.filter(status="published").count()
        draft_posts = obj.posts.filter(status="draft").count()

        return format_html(
            '<div style="background: #f9fafb; padding: 16px; border-radius: 8px;">'
            '<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">'

            '<div style="text-align: center;">'
            '<div style="font-size: 24px; font-weight: 700; color: #111827;">{}</div>'
            '<div style="font-size: 11px; color: #6b7280; margin-top: 4px;">Total Posts</div>'
            '</div>'

            '<div style="text-align: center;">'
            '<div style="font-size: 24px; font-weight: 700; color: #10b981;">{}</div>'
            '<div style="font-size: 11px; color: #6b7280; margin-top: 4px;">Published</div>'
            '</div>'

            '<div style="text-align: center;">'
            '<div style="font-size: 24px; font-weight: 700; color: #6b7280;">{}</div>'
            '<div style="font-size: 11px; color: #6b7280; margin-top: 4px;">Drafts</div>'
            '</div>'

            '</div></div>',
            total_posts,
            published_posts,
            draft_posts
        )

    user_stats.short_description = "User Statistics"


    @action(description="✓ Verify email addresses")
    def verify_emails(self, request, queryset):
        updated = queryset.update(email_verified=True)
        self.message_user(
            request,
            f"Successfully verified {updated} email address(es).",
        )

    @action(description="🔒 Enable MFA")
    def enable_mfa(self, request, queryset):
        updated = queryset.update(mfa_enabled=True)
        self.message_user(
            request,
            f"Successfully enabled MFA for {updated} user(s).",
        )

    @action(description="🔓 Disable MFA")
    def disable_mfa(self, request, queryset):
        updated = queryset.update(mfa_enabled=False)
        self.message_user(
            request,
            f"Successfully disabled MFA for {updated} user(s).",
        )

    @action(description="✍️ Make Author")
    def make_author(self, request, queryset):
        updated = queryset.update(role=Role.AUTHOR)
        self.message_user(
            request,
            f"Successfully changed {updated} user(s) to Author role.",
        )

    @action(description="👑 Make Admin")
    def make_admin(self, request, queryset):
        updated = queryset.update(role=Role.ADMIN)
        self.message_user(
            request,
            f"Successfully changed {updated} user(s) to Admin role.",
        )

    @action(description="❌ Deactivate users")
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f"Successfully deactivated {updated} user(s).",
        )

    @action(description="✓ Activate users")
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f"Successfully activated {updated} user(s).",
        )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("posts", "groups")


admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(ModelAdmin):
    search_fields = ["name"]
    filter_horizontal = ["permissions"]