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


# Level 1 — First Queries


def categories_by_name() -> QuerySet[Category]:
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
    return Post.objects.filter(slug=slug).first()


def active_users_count() -> int:
    """Return the number of active users who are not staff."""
    return User.objects.filter(is_active=True, is_staff=False).count()


def has_drafts() -> bool:
    """Return True if there is at least one draft post."""
    return Post.objects.filter(status=Post.Status.DRAFT).exists()


def published_posts_page(page: int) -> QuerySet[Post]:
    """Return one page (10 posts) of published posts, newest first."""
    start = (page - 1) * PAGE_SIZE
    return published_posts()[start : start + PAGE_SIZE]


# Level 2 — Field Lookups


def posts_with_word_in_title(word: str) -> QuerySet[Post]:
    """Return posts whose title contains the word, ignoring case."""
    return Post.objects.filter(title__icontains=word)


def users_with_email_domain(domain: str) -> QuerySet[User]:
    """Return users whose email ends with @domain."""
    return User.objects.filter(email__iendswith=f"@{domain}")


def posts_without_category() -> QuerySet[Post]:
    """Return posts that have no category."""
    return Post.objects.filter(category__isnull=True)


def categories_by_slugs(slugs: list[str]) -> QuerySet[Category]:
    """Return categories whose slug is in the list."""
    return Category.objects.filter(slug__in=slugs)


def posts_in_month(year: int, month: int) -> QuerySet[Post]:
    """Return posts created in this month of this year."""
    return Post.objects.filter(created_at__year=year, created_at__month=month)


def posts_last_days(days: int) -> QuerySet[Post]:
    """Return posts created in the last `days` days."""
    since = timezone.now() - timedelta(days=days)
    return Post.objects.filter(created_at__gte=since)


def posts_between(start: date, end: date) -> QuerySet[Post]:
    """Return posts created from start to end, both days included."""
    return Post.objects.filter(created_at__date__range=(start, end))


# Level 3 — Queries Across Relations


def author_published_posts(email: str) -> QuerySet[Post]:
    """Return published posts of the author with this email."""
    return published_posts().filter(author__email__iexact=email)


def posts_with_tag(tag_slug: str) -> QuerySet[Post]:
    """Return posts that have the tag with this slug."""
    return Post.objects.filter(tags__slug=tag_slug)


def comments_in_category(category_slug: str) -> QuerySet[Comment]:
    """Return comments on posts of the category with this slug."""
    return Comment.objects.filter(post__category__slug=category_slug)


def users_with_published_posts() -> QuerySet[User]:
    """Return users with at least one published post, each user once."""
    return User.objects.filter(post__status=Post.Status.PUBLISHED).distinct()


def posts_without_tags() -> QuerySet[Post]:
    """Return posts that have no tags."""
    return Post.objects.filter(tags__isnull=True)


def users_without_comments() -> QuerySet[User]:
    """Return users who have never written a comment."""
    return User.objects.filter(comment__isnull=True)


def posts_with_both_tags(first_slug: str, second_slug: str) -> QuerySet[Post]:
    """Return posts that have both tags."""
    return Post.objects.filter(tags__slug=first_slug).filter(
        tags__slug=second_slug
    )


# Level 4 — Q and F


def search_posts(text: str) -> QuerySet[Post]:
    """Return posts with the text in the title or in the body."""
    return Post.objects.filter(Q(title__icontains=text) | Q(body__icontains=text))


def published_posts_missing_info() -> QuerySet[Post]:
    """Return published posts without a category or without tags."""
    return (
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .filter(Q(category__isnull=True) | Q(tags__isnull=True))
        .distinct()
    )


def edited_posts() -> QuerySet[Post]:
    """Return posts edited more than 1 hour after they were created."""
    return Post.objects.filter(updated_at__gt=F("created_at") + EDIT_THRESHOLD)


def comments_by_post_author() -> QuerySet[Comment]:
    """Return comments written by the author of the post."""
    return Comment.objects.filter(author=F("post__author"))


def comments_before_post() -> QuerySet[Comment]:
    """Return comments created before their post (must be empty)."""
    return Comment.objects.filter(created_at__lt=F("post__created_at"))


# Level 5 — values and values_list


def published_authors_emails() -> list[str]:
    """Return unique emails of authors with published posts, A → Z."""
    return list(
        User.objects.filter(post__status=Post.Status.PUBLISHED)
        .values_list("email", flat=True)
        .distinct()
        .order_by("email")
    )


def published_posts_overview() -> list[dict[str, Any]]:
    """Return title, author_email and category_name of published posts."""
    return list(
        Post.objects.filter(status=Post.Status.PUBLISHED).values(
            "title",
            author_email=F("author__email"),
            category_name=Coalesce(F("category__name"), Value(UNCATEGORIZED)),
        )
    )


# Level 6 — aggregate


def posts_stats() -> dict[str, Any]:
    """Return post counts and the dates of the first and last post."""
    return Post.objects.aggregate(
        total=Count("id"),
        published=Count("id", filter=Q(status=Post.Status.PUBLISHED)),
        drafts=Count("id", filter=Q(status=Post.Status.DRAFT)),
        first_post_at=Min("created_at"),
        last_post_at=Max("created_at"),
    )


def average_comments_per_post() -> float:
    """Return the average number of comments on a published post."""
    result = (
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .annotate(comment_count=Count("comment"))
        .aggregate(average=Avg("comment_count", default=0.0))
    )
    return round(result["average"], AVERAGE_DIGITS)


# Level 7 — annotate


def categories_with_post_count() -> QuerySet[Category]:
    """Return categories with post_count, most posts first."""
    return Category.objects.annotate(post_count=Count("post")).order_by(
        "-post_count", "name"
    )


def categories_with_published_count() -> QuerySet[Category]:
    """Return every category with the number of its published posts."""
    return Category.objects.annotate(
        published_count=Count(
            "post",
            filter=Q(post__status=Post.Status.PUBLISHED),
        )
    ).order_by("-published_count", "name")


def top_authors() -> QuerySet[User]:
    """Return the top 5 users by number of published posts."""
    return User.objects.annotate(
        published_count=Count(
            "post",
            filter=Q(post__status=Post.Status.PUBLISHED),
        )
    ).order_by("-published_count", "email")[:TOP_AUTHORS_LIMIT]


def popular_tags(min_posts: int) -> QuerySet[Tag]:
    """Return tags used in at least min_posts posts, with post_count."""
    return (
        Tag.objects.annotate(post_count=Count("post"))
        .filter(post_count__gte=min_posts)
        .order_by("-post_count", "name")
    )


def posts_per_status() -> list[dict[str, Any]]:
    """Return the number of posts for each status."""
    return list(
        Post.objects.values("status")
        .annotate(count=Count("id"))
        .order_by("status")
    )


def users_activity() -> QuerySet[User]:
    """Return every user with correct post_count and comment_count."""
    return User.objects.annotate(
        post_count=Count("post", distinct=True),
        comment_count=Count("comment", distinct=True),
    ).order_by("email")


# Level 8 — Database Functions and Conditions


def search_users_by_full_name(text: str) -> QuerySet[User]:
    """Return users whose full name contains the text, ignoring case."""
    return User.objects.annotate(
        full_name=Concat("first_name", Value(" "), "last_name")
    ).filter(full_name__icontains=text)


def published_posts_per_month() -> list[dict[str, Any]]:
    """Return the number of published posts per month, oldest first."""
    return list(
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )


def posts_with_popularity() -> QuerySet[Post]:
    """Return posts with comment_count and popularity."""
    return (
        Post.objects.annotate(comment_count=Count("comment"))
        .annotate(
            popularity=Case(
                When(
                    comment_count__gte=HOT_MIN_COMMENTS,
                    then=Value(POPULARITY_HOT),
                ),
                When(
                    comment_count__gte=NORMAL_MIN_COMMENTS,
                    then=Value(POPULARITY_NORMAL),
                ),
                default=Value(POPULARITY_QUIET),
            )
        )
        .order_by("-comment_count")
    )


# Level 9 — Changing Data


def get_or_create_tag(name: str) -> tuple[Tag, bool]:
    """Return the tag with this name, create it if it does not exist."""
    return Tag.objects.get_or_create(
        slug=slugify(name),
        defaults={"name": name},
    )


def publish_old_drafts(days: int) -> int:
    """Publish drafts older than `days` days, return how many changed."""
    now = timezone.now()
    return Post.objects.filter(
        status=Post.Status.DRAFT,
        created_at__lt=now - timedelta(days=days),
    ).update(status=Post.Status.PUBLISHED, updated_at=now)


def tag_category_posts(category_slug: str, tag_slug: str) -> int:
    """Add the tag to every post of the category, return the post count."""
    tag = Tag.objects.get(slug=tag_slug)
    posts = list(Post.objects.filter(category__slug=category_slug))
    tag.post_set.add(*posts)
    return len(posts)


def merge_categories(source_slug: str, target_slug: str) -> int:
    """Move posts to the target category and delete the source one."""
    with transaction.atomic():
        source = Category.objects.get(slug=source_slug)
        target = Category.objects.get(slug=target_slug)
        moved = Post.objects.filter(category=source).update(category=target)
        source.delete()
    return moved


def delete_inactive_users_comments() -> int:
    """Delete all comments of inactive users, return how many."""
    deleted, _ = Comment.objects.filter(author__is_active=False).delete()
    return deleted


# Level 10 — select_related and prefetch_related


def published_feed() -> list[str]:
    """Return 50 newest published posts as 'title | email | category'."""
    posts = published_posts().select_related("author", "category")[
        :FEED_LIMIT
    ]
    lines = []
    for post in posts:
        category_name = post.category.name if post.category else UNCATEGORIZED
        lines.append(f"{post.title} | {post.author.email} | {category_name}")
    return lines


def newest_posts_with_tags() -> list[str]:
    """Return 20 newest posts as 'title: tag1, tag2'."""
    posts = Post.objects.prefetch_related("tags").order_by("-created_at")[
        :POSTS_WITH_TAGS_LIMIT
    ]
    lines = []
    for post in posts:
        tag_names = ", ".join(tag.name for tag in post.tags.all())
        lines.append(f"{post.title}: {tag_names}")
    return lines


def categories_with_published_posts() -> dict[str, list[str]]:
    """Return {category name: titles of its published posts}."""
    categories = Category.objects.prefetch_related(
        Prefetch(
            "post_set",
            queryset=published_posts(),
            to_attr="published_posts",
        )
    ).order_by("name")
    return {
        category.name: [post.title for post in category.published_posts]
        for category in categories
    }


# Level 11 — Subquery and Exists


def posts_with_last_comment() -> QuerySet[Post]:
    """Return published posts with the body of their newest comment."""
    newest_comment = (
        Comment.objects.filter(post=OuterRef("pk"))
        .order_by("-created_at")
        .values("body")[:1]
    )
    return published_posts().annotate(last_comment=Subquery(newest_comment))


def posts_with_staff_comments() -> QuerySet[Post]:
    """Return posts with at least one comment from a staff user."""
    staff_comments = Comment.objects.filter(
        post=OuterRef("pk"),
        author__is_staff=True,
    )
    return Post.objects.filter(Exists(staff_comments))


def users_with_draft_as_latest_post() -> QuerySet[User]:
    """Return users whose newest post is a draft."""
    newest_post = (
        Post.objects.filter(author=OuterRef("pk"))
        .order_by("-created_at")
        .values("status")[:1]
    )
    return User.objects.annotate(
        latest_post_status=Subquery(newest_post)
    ).filter(latest_post_status=Post.Status.DRAFT)


QUERIES: dict[int, Callable[..., Any]] = {
    1: categories_by_name,
    2: published_posts,
    3: newest_published_posts,
    4: post_by_slug,
    5: active_users_count,
    6: has_drafts,
    7: published_posts_page,
    8: posts_with_word_in_title,
    9: users_with_email_domain,
    10: posts_without_category,
    11: categories_by_slugs,
    12: posts_in_month,
    13: posts_last_days,
    14: posts_between,
    15: author_published_posts,
    16: posts_with_tag,
    17: comments_in_category,
    18: users_with_published_posts,
    19: posts_without_tags,
    20: users_without_comments,
    21: posts_with_both_tags,
    22: search_posts,
    23: published_posts_missing_info,
    24: edited_posts,
    25: comments_by_post_author,
    26: comments_before_post,
    27: published_authors_emails,
    28: published_posts_overview,
    29: posts_stats,
    30: average_comments_per_post,
    31: categories_with_post_count,
    32: categories_with_published_count,
    33: top_authors,
    34: popular_tags,
    35: posts_per_status,
    36: users_activity,
    37: search_users_by_full_name,
    38: published_posts_per_month,
    39: posts_with_popularity,
    40: get_or_create_tag,
    41: publish_old_drafts,
    42: tag_category_posts,
    43: merge_categories,
    44: delete_inactive_users_comments,
    45: published_feed,
    46: newest_posts_with_tags,
    47: categories_with_published_posts,
    48: posts_with_last_comment,
    49: posts_with_staff_comments,
    50: users_with_draft_as_latest_post,
}
