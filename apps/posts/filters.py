import django_filters
from django.db import connection
from django.db.models import Q
from django_filters.filters import BaseInFilter, CharFilter, DateFromToRangeFilter

from apps.posts.models import Post


class CharInFilter(BaseInFilter, django_filters.CharFilter):
    """Accept comma separated list (e.g. ?tags=python,django)."""


def _is_postgres() -> bool:
    return connection.vendor == "postgresql"


class PostFilter(django_filters.FilterSet):
    """
    FilterSet for posts:
     - category  -> category__name (exact or partial)
     - tags      -> comma separated tag slugs or names
     - author    -> author first or last name (partial)
     - published_between -> published_at range
     - status
    """

    category = CharFilter(field_name="category__name", lookup_expr="icontains")
    tags = CharInFilter(method="filter_tags")  # ?tags=python,django
    author = CharFilter(method="filter_author")  # matches first_name or last_name (icontains)
    published = DateFromToRangeFilter(field_name="published_at")
    status = django_filters.CharFilter(field_name="status", lookup_expr="iexact")

    class Meta:
        model = Post
        fields = ["category", "tags", "author", "published", "status"]

    def filter_tags(self, queryset, name, value):
        if not value:
            return queryset
        print(value)
        values = [v.strip() for v in value if v.strip()]
        # Search by tag slug OR tag name
        return queryset.filter(Q(tags__slug__in=values) | Q(tags__name__in=values))

    def filter_author(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(author__first_name__icontains=value) | Q(author__last_name__icontains=value)
        )
