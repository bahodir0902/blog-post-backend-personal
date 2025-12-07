from django.contrib import admin
from django.utils.html import format_html
from django.utils.timezone import now
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action

from .models import Post, PostImage, Reaction, ReactionType


class PostImageInline(TabularInline):
    model = PostImage
    extra = 1
    fields = ("image_preview", "image", "alt_text", "caption", "sort_order", "size_info")
    readonly_fields = ("image_preview", "size_info")

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 100px; border-radius: 8px;" />',
                obj.image.url
            )
        return "No image"

    image_preview.short_description = "Preview"

    def size_info(self, obj):
        if obj.size:
            size_mb = obj.size / (1024 * 1024)
            return format_html(
                '<span style="font-size: 11px;">{:.2f} MB<br/>{}</span>',
                size_mb,
                obj.content_type or "Unknown"
            )
        return "-"

    size_info.short_description = "File Info"


@admin.register(Post)
class PostAdmin(ModelAdmin):
    # Unfold configuration
    compressed_fields = True
    warn_unsaved_form = True

    list_display = [
        "title_with_badge",
        "author_link",
        "category_display",
        "status_badge",
        "published_date",
        "images_count",
        "created_display"
    ]

    list_filter = [
        "status",
        "created_at",
        "published_at",
        "category",
        "author",
    ]

    list_filter_submit = True

    search_fields = ["title", "short_description", "author__email", "author__first_name"]

    readonly_fields = [
        "slug",
        "created_at",
        "updated_at",
        "content_preview",
        "cover_preview"
    ]
    filter_horizontal = ["tags"]
    fieldsets = (
        ("📝 Post Information", {
            "fields": ("title", "slug", "category", "author", "status"),
            "description": "Basic information about the post"
        }),
        ("🏷️ Tags", {
            "fields": ("tags",),
        }),
        ("🎨 Content", {
            "fields": ("short_description", "content", "content_preview"),
        }),
        ("🖼️ Media", {
            "fields": ("cover_image", "cover_preview"),
        }),
        ("📅 Publishing", {
            "fields": ("published_at",),
        }),
        ("ℹ️ Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ["collapse"],
        }),
    )

    inlines = [PostImageInline]

    autocomplete_fields = ["author", "category"]

    date_hierarchy = "created_at"

    list_per_page = 25

    actions = ["make_published", "make_draft", "make_archived"]

    # Custom display methods
    def title_with_badge(self, obj):
        max_length = 60
        title = obj.title if len(obj.title) <= max_length else obj.title[:max_length] + "..."
        return title

    title_with_badge.short_description = "Title"
    title_with_badge.admin_order_field = "title"

    def author_link(self, obj):
        author_name = f"{obj.author.first_name} {obj.author.last_name or ''}".strip() or obj.author.email
        return format_html('<a href="/admin/users/user/{}/change/">{}</a>', obj.author.id,
                           author_name)

    author_link.short_description = "Author"
    author_link.admin_order_field = "author__email"

    def category_display(self, obj):
        if obj.category:
            return obj.category.name
        return "-"

    category_display.short_description = "Category"
    category_display.admin_order_field = "category__name"

    def status_badge(self, obj):
        icons = {
            Post.Status.PUBLISHED: "✓ ",
            Post.Status.DRAFT: "✎ ",
            Post.Status.SCHEDULED: "⏰ ",
            Post.Status.ARCHIVED: "📦 ",
        }
        icon = icons.get(obj.status, "")
        return f"{icon}{obj.get_status_display()}"

    status_badge.short_description = "Status"
    status_badge.admin_order_field = "status"

    def published_date(self, obj):
        if obj.published_at:
            if obj.published_at > now():
                return f"⏰ {obj.published_at.strftime('%b %d, %Y %H:%M')}"
            return f"✓ {obj.published_at.strftime('%b %d, %Y')}"
        return "-"

    published_date.short_description = "Published"
    published_date.admin_order_field = "published_at"

    def images_count(self, obj):
        count = obj.images.count()
        return f"🖼️ {count}" if count > 0 else "-"

    images_count.short_description = "Images"

    def created_display(self, obj):
        return obj.created_at.strftime("%b %d, %Y")

    created_display.short_description = "Created"
    created_display.admin_order_field = "created_at"

    def content_preview(self, obj):
        if obj.content and isinstance(obj.content, dict):
            content_blocks = obj.content.get("content", [])
            text_preview = ""
            for block in content_blocks[:3]:  # First 3 blocks
                if block.get("type") == "paragraph":
                    text = "".join([
                        item.get("text", "")
                        for item in block.get("content", [])
                        if item.get("type") == "text"
                    ])
                    text_preview += text + " "

            if text_preview:
                preview = text_preview[:200] + "..." if len(text_preview) > 200 else text_preview
                return format_html(
                    '<div style="background: #f9fafb; padding: 12px; border-radius: 6px; '
                    'border-left: 3px solid #3b82f6; max-width: 600px;">'
                    '<p style="margin: 0; color: #4b5563; font-size: 13px; line-height: 1.5;">{}</p>'
                    '</div>',
                    preview
                )
        return format_html('<span style="color: #9ca3af;">No content available</span>')

    content_preview.short_description = "Content Preview"

    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html(
                '<img src="{}" style="max-width: 400px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);" />',
                obj.cover_image.url
            )
        return format_html('<span style="color: #9ca3af;">No cover image</span>')

    cover_preview.short_description = "Cover Image Preview"

    @action(description="✓ Publish selected posts")
    def make_published(self, request, queryset):
        updated = queryset.update(status=Post.Status.PUBLISHED, published_at=now())
        self.message_user(
            request,
            f"Successfully published {updated} post(s).",
        )

    @action(description="✎ Move to Draft")
    def make_draft(self, request, queryset):
        updated = queryset.update(status=Post.Status.DRAFT)
        self.message_user(
            request,
            f"Successfully moved {updated} post(s) to draft.",
        )

    @action(description="📦 Archive selected posts")
    def make_archived(self, request, queryset):
        updated = queryset.update(status=Post.Status.ARCHIVED)
        self.message_user(
            request,
            f"Successfully archived {updated} post(s).",
        )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("author", "category").prefetch_related("images")


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    pass


@admin.register(ReactionType)
class ReactionTypeAdmin(admin.ModelAdmin):
    pass
# @admin.register(PostImage)
# class PostImageAdmin(ModelAdmin):
#     compressed_fields = True
#
#     list_display = [
#         "image_thumbnail",
#         "post_link",
#         "alt_text_display",
#         "order_badge",
#         "file_info",
#         "upload_date"
#     ]
#
#     list_filter = [
#         "post",
#         "created_at",
#     ]
#
#     search_fields = ["alt_text", "caption", "post__title", "original_name"]
#
#     readonly_fields = ["image_preview_large", "original_name", "size", "content_type", "created_at"]
#
#     fieldsets = (
#         ("🖼️ Image", {
#             "fields": ("image", "image_preview_large", "post"),
#         }),
#         ("📝 Details", {
#             "fields": ("alt_text", "caption", "sort_order"),
#         }),
#         ("📊 Metadata", {
#             "fields": ("original_name", "size", "content_type", "created_at"),
#             "classes": ["collapse"],
#         }),
#     )
#
#     autocomplete_fields = ["post"]
#
#     list_per_page = 30
#
#     def image_thumbnail(self, obj):
#         if obj.image:
#             return format_html(
#                 '<img src="{}" style="width: 60px; height: 60px; object-fit: cover; '
#                 'border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />',
#                 obj.image.url
#             )
#         return "No image"
#
#     image_thumbnail.short_description = "Preview"
#
#     def post_link(self, obj):
#         if obj.post:
#             title = obj.post.title[:40] + "..." if len(obj.post.title) > 40 else obj.post.title
#             return format_html(
#                 '<a href="/admin/posts/post/{}/change/">{}</a>',
#                 obj.post.id,
#                 title
#             )
#         return "Unassigned"
#
#     post_link.short_description = "Post"
#     post_link.admin_order_field = "post__title"
#
#     def alt_text_display(self, obj):
#         if obj.alt_text:
#             text = obj.alt_text[:50] + "..." if len(obj.alt_text) > 50 else obj.alt_text
#             return text
#         return format_html(
#             '<span style="color: #ef4444; font-size: 11px;">⚠️ Missing alt text</span>')
#
#     alt_text_display.short_description = "Alt Text"
#
#     def order_badge(self, obj):
#         return format_html(
#             '<span style="background: #e5e7eb; color: #374151; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 11px;"># {}</span>',
#             obj.sort_order
#         )
#
#     order_badge.short_description = "Order"
#     order_badge.admin_order_field = "sort_order"
#
#     def file_info(self, obj):
#         if obj.size:
#             size_mb = obj.size / (1024 * 1024)
#             return format_html(
#                 '<div>{:.2f} MB<br/><small>{}</small></div>',
#                 size_mb,
#                 obj.content_type or "Unknown"
#             )
#         return "-"
#
#     file_info.short_description = "File Info"
#
#     def upload_date(self, obj):
#         return obj.created_at.strftime("%b %d, %Y")
#
#     upload_date.short_description = "Uploaded"
#     upload_date.admin_order_field = "created_at"
#
#     def image_preview_large(self, obj):
#         if obj.image:
#             return format_html(
#                 '<img src="{}" style="max-width: 100%; max-height: 500px; border-radius: 8px; '
#                 'box-shadow: 0 4px 6px rgba(0,0,0,0.1);" />',
#                 obj.image.url
#             )
#         return "No image"
#
#     image_preview_large.short_description = "Image Preview"
#
#     def get_queryset(self, request):
#         qs = super().get_queryset(request)
#         return qs.select_related("post")
