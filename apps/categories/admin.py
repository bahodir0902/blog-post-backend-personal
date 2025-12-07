from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display
from unfold.contrib.filters.admin import RangeDateFilter

from .models import Category  # Adjust import based on your model


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    compressed_fields = True

    list_display = [
        "name_with_icon",
        "posts_count",
        "created_display",
    ]

    # REQUIRED for autocomplete_fields to work
    search_fields = ["name"]

    list_filter = [
        ("created_at", RangeDateFilter),
    ]

    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Category Information", {
            "fields": ("name",),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ["collapse"],
        }),
    )


    list_per_page = 30

    @display(description="Category Name", ordering="name")
    def name_with_icon(self, obj):
        return obj.name


    @display(description="Posts")
    def posts_count(self, obj):
        count = obj.posts.count() if hasattr(obj, 'posts') else 0
        if count > 0:
            return format_html(
                '<a href="/admin/posts/post/?category__id__exact={}" style="text-decoration: none;">'
                '<span style="background: #dbeafe; color: #1e40af; padding: 4px 10px; '
                'border-radius: 6px; font-size: 11px; font-weight: 600;">📝 {}</span>'
                '</a>',
                obj.id,
                count
            )
        return format_html('<span style="color: #9ca3af; font-size: 11px;">No posts</span>')

    @display(description="Created", ordering="created_at")
    def created_display(self, obj):
        return format_html(
            '<span style="color: #6b7280; font-size: 11px;">{}</span>',
            obj.created_at.strftime("%b %d, %Y")
        )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(posts_count=Count("posts"))