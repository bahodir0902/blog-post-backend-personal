# Put this in your main project's admin.py or in a separate admin configuration file

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.sites import UnfoldAdminSite


class CustomAdminSite(UnfoldAdminSite):
    """Custom admin site with enhanced features"""

    site_header = "Your Blog Admin"
    site_title = "Blog Admin Portal"
    index_title = "Welcome to Your Blog Administration"

    def each_context(self, request):
        context = super().each_context(request)

        # Add custom dashboard statistics
        if request.user.is_authenticated:
            from apps.posts.models import Post
            from apps.users.models import User

            context.update({
                'custom_stats': {
                    'total_posts': Post.objects.count(),
                    'published_posts': Post.objects.filter(status='published').count(),
                    'draft_posts': Post.objects.filter(status='draft').count(),
                    'total_users': User.objects.count(),
                    'active_users': User.objects.filter(is_active=True).count(),
                    'verified_users': User.objects.filter(email_verified=True).count(),
                }
            })

        return context

# Optional: Replace the default admin site
# admin.site = CustomAdminSite()
# admin.site.__class__ = CustomAdminSite


def dashboard_callback(request, context):
    """
    Add custom dashboard statistics and widgets
    """
    from apps.posts.models import Post
    from apps.users.models import User
    from django.utils.timezone import now
    from datetime import timedelta

    # Recent activity
    recent_posts = Post.objects.order_by('-created_at')[:5]
    recent_users = User.objects.order_by('-date_joined')[:5]

    # Statistics for last 30 days
    thirty_days_ago = now() - timedelta(days=30)

    context.update({
        "custom_dashboard": {
            "recent_posts": recent_posts,
            "recent_users": recent_users,
            "stats_30_days": {
                "new_posts": Post.objects.filter(created_at__gte=thirty_days_ago).count(),
                "new_users": User.objects.filter(date_joined__gte=thirty_days_ago).count(),
                "published_posts": Post.objects.filter(
                    status='published',
                    published_at__gte=thirty_days_ago
                ).count(),
            }
        }
    })

    return context
