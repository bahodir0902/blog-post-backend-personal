from django.db.models import Manager


class PublishedPostManager(Manager):
    def get_queryset(self):
        from apps.posts.models import Post

        return super().get_queryset().filter(status=Post.Status.PUBLISHED)
