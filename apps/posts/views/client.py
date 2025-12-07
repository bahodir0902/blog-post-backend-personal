import logging

from django.core.cache import cache
from django.db.models import Count, Q
from django.http import HttpRequest
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.bookmarks.models import Bookmark
from apps.common.pagination import PostPageNumberPagination
from apps.favourites.models import Favourite
from apps.posts.filters import PostFilter
from apps.posts.models import Post, Reaction, ReactionType
from apps.posts.serializers import (
    PostDetailSerializer,
    PostListSerializer,
    PostReactionsSerializer,
    ReactionPutSerializer,
)
from apps.posts.services import get_post_views, register_post_view
from apps.posts.trigram_search import TrigramSearchFilter
from apps.posts.utils import get_viewer_id
from apps.tags.serializers import TagSerializer
from apps.users.models.user import Role, User

logger = logging.getLogger(__name__)


@extend_schema(tags=["Posts"])
class ClientPostViewSet(ReadOnlyModelViewSet):
    lookup_field = "slug"

    filter_backends = [DjangoFilterBackend, TrigramSearchFilter, OrderingFilter]
    filterset_class = PostFilter

    search_fields = ["title", "short_description"]
    ordering_fields = ["published_at", "created_at"]
    pagination_class = PostPageNumberPagination

    def get_queryset(self):
        user = self.request.user
        base = (
            Post.objects.select_related("author", "category")
            .prefetch_related("images", "allowed_reactions", "comments")
            .order_by("-published_at")
        )

        if user.is_anonymous:
            return base.filter(status=Post.Status.PUBLISHED)

        if user.role == Role.ADMIN:
            return base

        elif user.role == Role.AUTHOR:
            return base.filter(Q(author=user) | Q(status=Post.Status.PUBLISHED))

        return base.filter(status=Post.Status.PUBLISHED)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PostDetailSerializer
        elif self.action == "put_reaction":
            return ReactionPutSerializer
        elif self.action in ["list_reactions", "remove_reaction"]:
            return PostReactionsSerializer
        elif self.action == "tags":
            return TagSerializer
        return PostListSerializer

    def get_permissions(self):
        if self.action in ["favourite", "bookmark", "put_reaction"]:
            return [IsAuthenticated()]
        return [AllowAny()]

    def paginate_queryset(self, queryset):
        if self.action == "list":
            return super().paginate_queryset(queryset)
        return None

    def _get_cache_key_for_list(self, request):
        """Generate cache key for list endpoint including all filters"""
        user_role = "anon" if request.user.is_anonymous else request.user.role
        user_id = "anon" if request.user.is_anonymous else request.user.id

        # Include query params in cache key
        query_params = request.GET.urlencode()
        return f"post_list:{user_role}:{user_id}:{query_params}"

    def list(self, request, *args, **kwargs):
        cache_key = self._get_cache_key_for_list(request)
        cached_response = cache.get(cache_key)

        if cached_response:
            logger.debug("[CACHE] Post list cache hit - key=%s", cache_key)
            return Response(cached_response)

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            # Cache the entire paginated response structure
            response = self.get_paginated_response(serializer.data)
            cache.set(cache_key, response.data, 60 * 5)  # 5 minutes
            logger.debug("[CACHE] Post list cached - key=%s", cache_key)
            return response

        serializer = self.get_serializer(queryset, many=True)
        cache.set(cache_key, serializer.data, 60 * 5)
        logger.debug("[CACHE] Post list cached - key=%s", cache_key)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        cache_key = f"post_detail:{instance.slug}"

        # Get cached post data
        post_data = cache.get(cache_key)

        if not post_data:
            serializer = self.get_serializer(instance)
            post_data = serializer.data
            cache.set(cache_key, post_data, 60 * 60 * 6)  # 6 hours
            logger.debug("[CACHE] Post detail cached - key=%s", cache_key)
        else:
            logger.debug("[CACHE] Post detail cache hit - key=%s", cache_key)

        # Handle view tracking without DB hits
        viewer_id, cookie_to_set = get_viewer_id(request)
        register_post_view(instance.pk, viewer_id)
        total, unique = get_post_views(instance.pk)

        # Merge cached data with view counts
        response_data = {**post_data, "views_total": total, "views_unique": unique}
        response = Response(response_data)

        if cookie_to_set:
            response.set_cookie(
                "viewer_id", cookie_to_set, max_age=31536000, samesite="None", secure=True
            )
        return response

    @action(methods=["get"], detail=False, url_path="latest-posts")
    def latest_posts(self, request):
        user_role = "anon" if request.user.is_anonymous else request.user.role
        cache_key = f"latest_posts:{user_role}"

        cached_data = cache.get(cache_key)
        if cached_data:
            logger.debug("[CACHE] Latest posts cache hit - key=%s", cache_key)
            return Response(cached_data)

        queryset = self.get_queryset()[:10]
        serializer = self.get_serializer(queryset, many=True)

        cache.set(cache_key, serializer.data, 60 * 10)  # 10 minutes
        logger.debug("[CACHE] Latest posts cached - key=%s", cache_key)
        return Response(serializer.data)

    @action(methods=["get"], detail=False, url_path="trending-posts")
    def trending_posts(self, request):
        user_role = "anon" if request.user.is_anonymous else request.user.role
        cache_key = f"trending_posts:{user_role}"

        cached_data = cache.get(cache_key)
        if cached_data:
            logger.debug("[CACHE] Trending posts cache hit - key=%s", cache_key)
            return Response(cached_data)

        queryset = self.get_queryset()[:10]
        serializer = self.get_serializer(queryset, many=True)

        cache.set(cache_key, serializer.data, 60 * 15)  # 15 minutes
        logger.debug("[CACHE] Trending posts cached - key=%s", cache_key)
        return Response(serializer.data)

    @action(methods=["get"], detail=False, url_path="most-popular-posts")
    def most_popular_posts(self, request):
        user_role = "anon" if request.user.is_anonymous else request.user.role
        cache_key = f"most_popular_posts:{user_role}"

        cached_data = cache.get(cache_key)
        if cached_data:
            logger.debug("[CACHE] Most popular posts cache hit - key=%s", cache_key)
            return Response(cached_data)

        queryset = self.get_queryset()[:10]
        serializer = self.get_serializer(queryset, many=True)

        cache.set(cache_key, serializer.data, 60 * 20)  # 20 minutes
        logger.debug("[CACHE] Most popular posts cached - key=%s", cache_key)
        return Response(serializer.data)

    @action(methods=["get"], detail=False, url_path="homepage-statistics")
    def homepage_statistics(self, request):
        cache_key = "homepage_statistics"

        cached_data = cache.get(cache_key)
        if cached_data:
            logger.debug("[CACHE] Homepage statistics cache hit - key=%s", cache_key)
            return Response(cached_data)

        articles = Post.objects.aggregate(
            articles=Count("id", filter=Q(status=Post.Status.PUBLISHED)),
        )["articles"]
        writers = User.objects.aggregate(
            writers=Count("id", filter=Q(role=Role.AUTHOR), distinct=True)
        )["writers"]

        data = {"Active Readers": "50000", "Articles": articles, "Writers": writers}

        cache.set(cache_key, data, 60 * 30)  # 30 minutes
        logger.debug("[CACHE] Homepage statistics cached - key=%s", cache_key)
        return Response(data)

    @action(methods=["get"], detail=True, url_path="related-posts")
    def related_posts(self, request, slug=None):
        post: Post = self.get_object()
        cache_key = f"related_posts:{post.slug}"

        cached_data = cache.get(cache_key)
        if cached_data:
            logger.debug("[CACHE] Related posts cache hit - key=%s", cache_key)
            return Response(cached_data)

        if not post.category:
            return Post.objects.none()
        qs = (
            post.category.posts.all()
            .exclude(slug=post.slug)
            .select_related("author", "category")
            .order_by("-published_at")[:3]
        )
        serializer = self.get_serializer(qs, many=True)

        cache.set(cache_key, serializer.data, 60 * 60)  # 1 hour
        logger.debug("[CACHE] Related posts cached - key=%s", cache_key)
        return Response(serializer.data)

    @action(methods=["post"], detail=True)
    def favourite(self, request: HttpRequest, slug=None):
        post: Post = self.get_object()
        user = request.user

        favourite, created = Favourite.objects.get_or_create(user=user, post=post)
        if created:
            logger.info(
                "[FAVOURITE] Post favourited - post_id=%s, slug=%s, user_id=%s",
                post.pk,
                post.slug,
                user.pk,
            )
        return Response({"detail": "Post favorited."}, status=status.HTTP_201_CREATED)

    @favourite.mapping.delete
    def remove_favourite(self, request, slug=None):
        post: Post = self.get_object()
        user = request.user

        deleted_count, _ = Favourite.objects.filter(user=user, post=post).delete()
        if deleted_count > 0:
            logger.info(
                "[FAVOURITE] Post unfavourited - post_id=%s, slug=%s, user_id=%s",
                post.pk,
                post.slug,
                user.pk,
            )
        return Response({"detail": "Favourite removed."}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def bookmark(self, request, slug=None):
        post = self.get_object()
        bookmark, created = Bookmark.objects.get_or_create(user=request.user, post=post)
        if created:
            logger.info(
                "[BOOKMARK] Post bookmarked - post_id=%s, slug=%s, user_id=%s",
                post.pk,
                post.slug,
                request.user.pk,
            )
        return Response({"detail": "Bookmarked"}, status=201)

    @bookmark.mapping.delete
    def remove_bookmark(self, request, slug=None):
        post = self.get_object()
        deleted_count, _ = Bookmark.objects.filter(user=request.user, post=post).delete()
        if deleted_count > 0:
            logger.info(
                "[BOOKMARK] Post unbookmarked - post_id=%s, slug=%s, user_id=%s",
                post.pk,
                post.slug,
                request.user.pk,
            )
        return Response(status=204)

    @action(methods=["post"], detail=True, url_path="put-reaction")
    def put_reaction(self, request, slug=None):
        post: Post = self.get_object()
        serializer = self.get_serializer(
            data=request.data, context={"request": request, "post": post}
        )
        serializer.is_valid(raise_exception=True)
        reaction = serializer.save()

        # Invalidate reaction cache for this post
        cache_keys = [f"post_reactions:{post.slug}:anon"]
        if request.user.is_authenticated:
            cache_keys.append(f"post_reactions:{post.slug}:{request.user.id}")
        cache.delete_many(cache_keys)
        logger.info(
            "[CACHE] Reaction cache invalidated - post_id=%s, slug=%s, keys=%s",
            post.pk,
            post.slug,
            cache_keys,
        )
        logger.info(
            "[REACTION] Post reaction added - post_id=%s, slug=%s, reaction_id=%s, user_id=%s",
            post.pk,
            post.slug,
            reaction.type_id if hasattr(reaction, "type_id") else "unknown",
            request.user.pk,
        )

        # Get allowed reactions for this post
        if post.allowed_reactions.exists():
            qs = post.allowed_reactions.all()
        else:
            qs = ReactionType.objects.all()

        qs = qs.annotate(count=Count("reactions", filter=Q(reactions__post=post))).order_by("id")

        # Prefetch user's reactions once to avoid N+1
        user_reaction_ids = set()
        if request.user.is_authenticated:
            user_reaction_ids = set(
                Reaction.objects.filter(user=request.user, post=post).values_list(
                    "type_id", flat=True
                )
            )

        out = PostReactionsSerializer(
            qs,
            many=True,
            context={"request": request, "post": post, "user_reactions": user_reaction_ids},
        )
        return Response(out.data, status=status.HTTP_201_CREATED)

    @put_reaction.mapping.delete
    def remove_reaction(self, request, slug=None):
        post = self.get_object()
        deleted_count, _ = Reaction.objects.filter(user=request.user, post=post).delete()

        # Invalidate reaction cache for this post
        cache_keys = [f"post_reactions:{post.slug}:anon"]
        if request.user.is_authenticated:
            cache_keys.append(f"post_reactions:{post.slug}:{request.user.id}")
        cache.delete_many(cache_keys)
        logger.info(
            "[CACHE] Reaction cache invalidated - post_id=%s, slug=%s, keys=%s",
            post.pk,
            post.slug,
            cache_keys,
        )
        if deleted_count > 0:
            logger.info(
                "[REACTION] Post reaction removed - post_id=%s, slug=%s, user_id=%s",
                post.pk,
                post.slug,
                request.user.pk,
            )

        # Get allowed reactions for this post
        if post.allowed_reactions.exists():
            qs = post.allowed_reactions.all()
        else:
            qs = ReactionType.objects.all()

        qs = qs.annotate(count=Count("reactions", filter=Q(reactions__post=post))).order_by("id")

        # No user reactions after deletion
        serializer = self.get_serializer(
            qs, many=True, context={"request": request, "post": post, "user_reactions": set()}
        )
        return Response(serializer.data)

    @action(methods=["get"], detail=True, url_path="list-reactions")
    def list_reactions(self, request, slug=None):
        post: Post = self.get_object()
        user_id = request.user.id if request.user.is_authenticated else "anon"
        cache_key = f"post_reactions:{post.slug}:{user_id}"

        cached_data = cache.get(cache_key)
        if cached_data:
            logger.debug("[CACHE] Post reactions cache hit - key=%s", cache_key)
            return Response(cached_data)

        # Get allowed reactions for this post
        if post.allowed_reactions.exists():
            qs = post.allowed_reactions.all()
        else:
            # If no specific reactions are set, no reactions allowed
            qs = ReactionType.objects.none()

        qs = qs.annotate(count=Count("reactions", filter=Q(reactions__post=post))).order_by("id")

        # Prefetch user's reactions once to avoid N+1
        user_reaction_ids = set()
        if request.user.is_authenticated:
            user_reaction_ids = set(
                Reaction.objects.filter(user=request.user, post=post).values_list(
                    "type_id", flat=True
                )
            )

        serializer = self.get_serializer(
            qs,
            many=True,
            context={"request": request, "post": post, "user_reactions": user_reaction_ids},
        )

        cache.set(cache_key, serializer.data, 60 * 5)  # 5 minutes
        logger.debug("[CACHE] Post reactions cached - key=%s", cache_key)
        return Response(serializer.data)

    @action(methods=["get"], detail=True)
    def tags(self, request, slug=None):
        post: Post = self.get_object()
        cache_key = f"post_tags:{post.slug}"

        cached_data = cache.get(cache_key)
        if cached_data:
            logger.debug("[CACHE] Post tags cache hit - key=%s", cache_key)
            return Response(cached_data)

        tags = post.tags.all()
        serializer = self.get_serializer(tags, many=True)

        cache.set(cache_key, serializer.data, 60 * 60 * 24)  # 24 hours
        logger.debug("[CACHE] Post tags cached - key=%s", cache_key)
        return Response(serializer.data)
