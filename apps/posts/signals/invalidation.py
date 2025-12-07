import logging

from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from apps.posts.models import Post, Reaction
from apps.posts.utils.invalidation import (
    invalidate_post_cache,
    invalidate_post_list_caches,
    invalidate_reaction_cache,
)

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Post)
def post_saved(sender, instance, created, **kwargs):
    """
    Invalidate caches when a post is created or updated.
    """
    action_type = "created" if created else "updated"
    logger.info(
        "[CACHE] Post %s, invalidating caches - post_id=%s, slug=%s",
        action_type,
        instance.pk,
        instance.slug,
    )
    # Invalidate the specific post cache
    invalidate_post_cache(instance)

    # Invalidate list caches (latest, trending, popular, etc.)
    invalidate_post_list_caches()


@receiver(post_delete, sender=Post)
def post_deleted(sender, instance, **kwargs):
    """
    Invalidate caches when a post is deleted.
    """
    logger.info(
        "[CACHE] Post deleted, invalidating caches - post_id=%s, slug=%s",
        instance.pk,
        instance.slug,
    )
    invalidate_post_cache(instance)
    invalidate_post_list_caches()


@receiver(m2m_changed, sender=Post.tags.through)
def post_tags_changed(sender, instance, action, **kwargs):
    """
    Invalidate post cache when tags are added/removed.
    """
    if action in ["post_add", "post_remove", "post_clear"]:
        logger.info(
            "[CACHE] Post tags changed (%s), invalidating cache - post_id=%s, slug=%s",
            action,
            instance.pk,
            instance.slug,
        )
        invalidate_post_cache(instance)


@receiver(m2m_changed, sender=Post.allowed_reactions.through)
def post_reactions_changed(sender, instance, action, **kwargs):
    """
    Invalidate reaction cache when allowed reactions change.
    """
    if action in ["post_add", "post_remove", "post_clear"]:
        logger.info(
            "[CACHE] Post allowed reactions changed (%s), invalidating cache - post_id=%s, slug=%s",
            action,
            instance.pk,
            instance.slug,
        )
        invalidate_reaction_cache(instance)


@receiver(post_save, sender=Reaction)
def reaction_saved(sender, instance, **kwargs):
    """
    Invalidate reaction cache when a reaction is created/updated.
    """
    logger.debug(
        "[CACHE] Reaction saved, invalidating cache - post_id=%s, slug=%s, user_id=%s",
        instance.post.pk,
        instance.post.slug,
        instance.user.id,
    )
    invalidate_reaction_cache(instance.post, instance.user.id)


@receiver(post_delete, sender=Reaction)
def reaction_deleted(sender, instance, **kwargs):
    """
    Invalidate reaction cache when a reaction is deleted.
    """
    logger.debug(
        "[CACHE] Reaction deleted, invalidating cache - post_id=%s, slug=%s, user_id=%s",
        instance.post.pk,
        instance.post.slug,
        instance.user.id,
    )
    invalidate_reaction_cache(instance.post, instance.user.id)
