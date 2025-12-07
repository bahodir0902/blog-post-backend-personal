from django.contrib.postgres.search import TrigramSimilarity
from django.db import connection
from django.db.models import F, Max, OuterRef, Q, Subquery
from django.db.models.functions import Greatest
from rest_framework.filters import BaseFilterBackend

DEFAULT_THRESHOLD = 0.15  # tuneable; 0.1-0.3 typical


class TrigramSearchFilter(BaseFilterBackend):
    """
    If ?q=... is provided:
     - On PostgreSQL: annotate similarity across multiple fields using TrigramSimilarity,
       filter by threshold (query param `min_sim`) and order by similarity desc.
     - On other DBs: fallback to OR'd icontains over the same fields.
    """

    search_param = "q"
    min_sim_param = "min_sim"

    def filter_queryset(self, request, queryset, view):
        q = request.query_params.get(self.search_param)
        if not q:
            return queryset

        # Allow caller to set a custom minimum similarity (float)
        try:
            min_sim = float(request.query_params.get(self.min_sim_param, DEFAULT_THRESHOLD))
        except (TypeError, ValueError):
            min_sim = DEFAULT_THRESHOLD

        if connection.vendor == "postgresql":
            # annotate similarity across fields and take the greatest value
            # use fields you asked for: title, short_description, text_content, slug,
            # author first/last, category name, tags name
            # Because tags is m2m, distinct() below removes duplicates.
            base = queryset.annotate(
                sim_title=TrigramSimilarity("title", q),
                sim_short=TrigramSimilarity("short_description", q),
                sim_text=TrigramSimilarity("text_content", q),
                sim_slug=TrigramSimilarity("slug", q),
                sim_author_first=TrigramSimilarity("author__first_name", q),
                sim_author_last=TrigramSimilarity("author__last_name", q),
                sim_category=TrigramSimilarity("category__name", q),
                sim_tag=TrigramSimilarity("tags__name", q),
            ).annotate(
                similarity=Greatest(
                    F("sim_title"),
                    F("sim_short"),
                    F("sim_text"),
                    F("sim_slug"),
                    F("sim_author_first"),
                    F("sim_author_last"),
                    F("sim_category"),
                    F("sim_tag"),
                )
            )
            max_sim_subquery = (
                base.filter(pk=OuterRef("pk"))
                .values("pk")
                .annotate(max_sim=Max("similarity"))
                .values("max_sim")
            )

            qs = queryset.annotate(similarity=Subquery(max_sim_subquery)).filter(
                similarity__gte=min_sim
            )

            # user ordering OR default fallback
            ordering = request.query_params.get("ordering")
            if ordering:
                return qs.order_by(ordering)

            return qs.order_by("-similarity", "-published_at")

        else:
            # Non-Postgres fallback: cheap partial match across the same fields.
            lookups = (
                Q(title__icontains=q)
                | Q(short_description__icontains=q)
                | Q(text_content__icontains=q)
                | Q(slug__icontains=q)
                | Q(author__first_name__icontains=q)
                | Q(author__last_name__icontains=q)
                | Q(category__name__icontains=q)
                | Q(tags__name__icontains=q)
            )
            return queryset.filter(lookups).distinct()
