import logging

from celery import shared_task
from django.utils import timezone

from .models import Post

logger = logging.getLogger(__name__)


@shared_task
def publish_scheduled_posts():
    now = timezone.now()

    posts = Post.objects.filter(
        status=Post.Status.SCHEDULED,
        published_at__lte=now,
    )
    try:
        count = posts.update(status=Post.Status.PUBLISHED)
    except Exception as e:
        logger.error(e)
        return "Error occurred while publishing scheduled posts."

    if count > 0:
        logger.info("Published %d scheduled posts.", count)

    return f"Published {count} posts."
