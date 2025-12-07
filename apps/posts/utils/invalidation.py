import logging

from django.core.cache import cache

from apps.users.models.user import Role

logger = logging.getLogger(__name__)


def invalidate_post_cache(post):
    """
    Invalidate all cache keys related to a specific post.
    Call this when a post is created, updated, or deleted.
    """
    cache_keys = [
        f"post_detail:{post.slug}",
        f"related_posts:{post.slug}",
        f"post_tags:{post.slug}",
        f"post_reactions:{post.slug}:anon",
    ]

    cache.delete_many(cache_keys)
    logger.info(
        "[CACHE] Post cache invalidated - post_id=%s, slug=%s, keys=%s",
        post.pk,
        post.slug,
        cache_keys,
    )


def invalidate_post_list_caches():
    """
    Invalidate all list-based caches.
    Call this when any post is created, updated, deleted, or published.
    """
    roles = ["anon", Role.ADMIN, Role.AUTHOR]
    cache_keys = []

    for role in roles:
        cache_keys.extend(
            [
                f"latest_posts:{role}",
                f"trending_posts:{role}",
                f"most_popular_posts:{role}",
            ]
        )

    cache_keys.append("homepage_statistics")
    cache.delete_many(cache_keys)
    logger.info("[CACHE] Post list caches invalidated - keys=%s", cache_keys)
    # Clear all list caches with filters (pattern-based deletion)
    # Note: This requires Redis backend
    try:
        from django_redis import get_redis_connection

        redis_conn = get_redis_connection("default")

        # Delete all post_list cache keys
        keys = redis_conn.keys("post_list:*")
        if keys:
            deleted_count = redis_conn.delete(*keys)
            logger.info(
                "[CACHE] Post list pattern caches invalidated - pattern=post_list:*, count=%s",
                deleted_count,
            )
    except Exception as e:
        # Fallback if Redis not available
        logger.warning("[CACHE] Failed to invalidate pattern caches: %s", str(e))
        pass


def invalidate_reaction_cache(post, user_id=None):
    """
    Invalidate reaction caches for a specific post.
    If user_id provided, invalidates only that user's cache.
    """
    if user_id:
        cache_key = f"post_reactions:{post.slug}:{user_id}"
        cache.delete(cache_key)
        logger.info(
            "[CACHE] Reaction cache invalidated - post_id=%s, slug=%s, user_id=%s, key=%s",
            post.pk,
            post.slug,
            user_id,
            cache_key,
        )
    else:
        # Invalidate for all users (when reaction counts change)
        cache.delete(f"post_reactions:{post.slug}:anon")
        logger.info(
            "[CACHE] Reaction cache invalidated (anon) - post_id=%s, slug=%s",
            post.pk,
            post.slug,
        )

        # If you need to clear all user-specific reaction caches
        try:
            from django_redis import get_redis_connection

            redis_conn = get_redis_connection("default")
            keys = redis_conn.keys(f"post_reactions:{post.slug}:*")
            if keys:
                deleted_count = redis_conn.delete(*keys)
                logger.info(
                    "[CACHE] Reaction pattern caches invalidated - post_id=%s, slug=%s,"
                    " pattern=post_reactions:%s:*, count=%s",
                    post.pk,
                    post.slug,
                    post.slug,
                    deleted_count,
                )
        except Exception as e:
            logger.warning("[CACHE] Failed to invalidate reaction pattern caches: %s", str(e))
            pass


def invalidate_category_cache(category_id):
    """
    Invalidate caches for posts in a specific category.
    Call this when a category is updated or deleted.
    """
    try:
        from django_redis import get_redis_connection

        redis_conn = get_redis_connection("default")

        # Delete all list caches that might include this category
        keys = redis_conn.keys("post_list:*")
        if keys:
            deleted_count = redis_conn.delete(*keys)
            logger.info(
                "[CACHE] Category cache invalidated - category_id=%s, pattern=post_list:*, "
                "count=%s",
                category_id,
                deleted_count,
            )
    except Exception as e:
        logger.warning("[CACHE] Failed to invalidate category caches: %s", str(e))
        pass

    invalidate_post_list_caches()
