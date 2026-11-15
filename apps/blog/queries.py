from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

from django.db import transaction
from django.db.models import (
    Avg,
    Case,
    Count,
    Exists,
    F,
    Max,
    Min,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Concat, TruncMonth
from django.utils import timezone
from django.utils.text import slugify

from apps.auths.models import User
from apps.blog.models import Category, Comment, Post, Tag

PAGE_SIZE = 10
NEWEST_POSTS_LIMIT = 5
TOP_AUTHORS_LIMIT = 5
FEED_LIMIT = 50
POSTS_WITH_TAGS_LIMIT = 20
EDIT_THRESHOLD = timedelta(hours=1)
AVERAGE_DIGITS = 2
UNCATEGORIZED = "Uncategorized"

HOT_MIN_COMMENTS = 10
NORMAL_MIN_COMMENTS = 3
POPULARITY_HOT = "hot"
POPULARITY_NORMAL = "normal"
POPULARITY_QUIET = "quiet"

def categories_by_name()-> QuerySet[Category]:
    """Return all categories sorted by name A -> Z."""
    return Category.objects.order_by("name")


def published_posts() -> QuerySet[Post]:
    """Return published posts, newest first."""
    return Post.objects.filter(status=Post.Status.PUBLISHED).order_by(
        "-created_at"
    )


def newest_published_posts() -> QuerySet[Post]:
    """Return the 5 newest published posts."""
    return published_posts()[:NEWEST_POSTS_LIMIT]


def post_by_slug(slug: str) -> Post | None:
    """Return the post with this slug or None."""
    return Post.objects.filter(slug=slug).first(
    )


def active_users_count() -> int:
    """Return the number of active users who are not staff."""
    return User.objects.filter(is_active = True, is_staff=False).count()


def has_drafts() -> bool:
    """Return True if there is at least one draft post."""
    return Post.objects.filter(status=Post.Status.DRAFT).exists()


def published_posts_page(page: int) -> QuerySet[Post]:
    """Return one page (10 posts) of published posts, newest first."""
    start = (page - 1) *PAGE_SIZE
    return published_posts()[start : start + PAGE_SIZE]


QUERIES: dict[int, Callable[..., Any]] = {
    1: categories_by_name,
    2: published_posts,
    3: newest_published_posts,
    4: post_by_slug,
    5: active_users_count,
    6: has_drafts,
    7: published_posts_page,
}
