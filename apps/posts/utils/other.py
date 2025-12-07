from django.core.cache import cache


def invalidate_post_cache(post_id):
    cache.delete(f"post:{post_id}:detail")
    cache.delete("post:list")
