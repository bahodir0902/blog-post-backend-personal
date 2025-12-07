from django_redis import get_redis_connection

redis = get_redis_connection("default")


def register_post_view(post_id: int, viewer_id: str):
    """
    Adds a view (unique + total) for the given post.
    """

    pipe = redis.pipeline()

    pipe.incr(f"post:{post_id}:views_total")

    pipe.sadd(f"post:{post_id}:views_unique", viewer_id)

    pipe.execute()


def get_post_views(post_id: int):
    """
    Returns (total_views, unique_views) from Redis.
    """
    pipe = redis.pipeline()

    pipe.get(f"post:{post_id}:views_total")
    pipe.scard(f"post:{post_id}:views_unique")
    total, unique = pipe.execute()

    return int(total or 0), int(unique or 0)
