
import random
import time
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.utils.text import slugify
from faker import Faker

from apps.blog.models import Category, Comment, Post, Tag

DEFAULT_USERS = 20
DEFAULT_POSTS = 100
DEFAULT_COMMENTS = 500

SEED_PASSWORD = "TestPassword123!"

ACTIVE_RATIO = 0.9
STAFF_RATIO = 0.1
PUBLISHED_RATIO = 0.7
NO_CATEGORY_RATIO = 0.1

MAX_TAGS_PER_POST = 5
POST_PARAGRAPHS = 3
MAX_COMMENT_SENTENCES = 3
POST_TITLE_WORDS = 6

CATEGORY_NAMES = [
    "Python",
    "Django",
    "DevOps",
    "Frontend",
    "Backend",
    "Databases",
    "Cloud",
    "Security",
]

TAG_NAMES = [
    "API",
    "REST",
    "JWT",
    "Docker",
    "Git",
    "PostgreSQL",
    "SQLite",
    "Redis",
    "Linux",
    "Testing",
    "Security",
    "Django REST",
    "Authentication",
    "Deployment",
    "CI/CD",
    "ORM",
    "Celery",
    "Async",
    "Cloud",
    "Tutorial",
]

User = get_user_model()
fake = Faker()


class Command(BaseCommand):
    help = "Fill the database with fake data."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--users",
            type=int,
            default=DEFAULT_USERS,
            help="Number of users to create",
        )
        parser.add_argument(
            "--posts",
            type=int,
            default=DEFAULT_POSTS,
            help="Number of posts to create",
        )
        parser.add_argument(
            "--comments",
            type=int,
            default=DEFAULT_COMMENTS,
            help="Number of comments to create",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing data before seeding",
        )

    def clear_data(self) -> None:
        Comment.objects.all().delete()
        Post.objects.all().delete()
        Tag.objects.all().delete()
        Category.objects.all().delete()

        User.objects.filter(
            is_superuser=False
        ).delete()

        self.stdout.write("Existing data cleared.")

    def create_users(self, count: int) -> int:
        used_emails = set(
            User.objects.values_list("email", flat=True)
        )

        users = []

        if count == 0:
            return 0

        password = make_password(SEED_PASSWORD)

        for _ in range(count):
            first_name = fake.first_name()
            last_name = fake.last_name()

            base_email = slugify(
                f"{first_name}.{last_name}"
            ).replace("-", ".")

            base_email = base_email or "user"

            email = f"{base_email}@example.com"
            number = 2

            while email in used_emails:
                email = (
                    f"{base_email}{number}@example.com"
                )
                number += 1

            used_emails.add(email)

            users.append(
                User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=password,
                    is_active=(
                        random.random() < ACTIVE_RATIO
                    ),
                    is_staff=(
                        random.random() < STAFF_RATIO
                    ),
                )
            )

        User.objects.bulk_create(users)

        return len(users)

    def create_categories(self) -> int:
        existing_names = set(
            Category.objects.values_list(
                "name", flat=True
            )
        )

        existing_slugs = set(
            Category.objects.values_list(
                "slug", flat=True
            )
        )

        categories = []

        for name in CATEGORY_NAMES:
            slug = slugify(name)

            if (
                name in existing_names
                or slug in existing_slugs
            ):
                continue

            categories.append(
                Category(
                    name=name,
                    slug=slug,
                )
            )

            existing_names.add(name)
            existing_slugs.add(slug)

        Category.objects.bulk_create(categories)

        return len(categories)

    def create_tags(self) -> int:
        existing_names = set(
            Tag.objects.values_list(
                "name", flat=True
            )
        )

        existing_slugs = set(
            Tag.objects.values_list(
                "slug", flat=True
            )
        )

        tags = []

        for name in TAG_NAMES:
            slug = slugify(name)

            if (
                name in existing_names
                or slug in existing_slugs
            ):
                continue

            tags.append(
                Tag(
                    name=name,
                    slug=slug,
                )
            )

            existing_names.add(name)
            existing_slugs.add(slug)

        Tag.objects.bulk_create(tags)

        return len(tags)

    def create_posts(self, count: int) -> int:
        if count == 0:
            return 0

        authors = list(User.objects.all())
        categories = list(Category.objects.all())
        tags = list(Tag.objects.all())

        if not authors:
            raise CommandError(
                "Cannot create posts without users."
            )

        used_slugs = set(
            Post.objects.values_list(
                "slug", flat=True
            )
        )

        posts = []

        for _ in range(count):
            title = fake.sentence(
                nb_words=POST_TITLE_WORDS
            ).rstrip(".")

            title = title[:200]

            base_slug = (
                slugify(title)[:40].rstrip("-")
                or "post"
            )

            slug = base_slug
            number = 2

            while slug in used_slugs:
                suffix = f"-{number}"
                slug = (
                    f"{base_slug[:50 - len(suffix)]}"
                    f"{suffix}"
                )
                number += 1

            used_slugs.add(slug)

            category = None

            if (
                categories
                and random.random() >= NO_CATEGORY_RATIO
            ):
                category = random.choice(categories)

            status = (
                Post.Status.PUBLISHED
                if random.random() < PUBLISHED_RATIO
                else Post.Status.DRAFT
            )

            posts.append(
                Post(
                    author=random.choice(authors),
                    title=title,
                    slug=slug,
                    body="\n\n".join(
                        fake.paragraphs(
                            nb=POST_PARAGRAPHS
                        )
                    ),
                    category=category,
                    status=status,
                )
            )

        Post.objects.bulk_create(posts)

        for post in posts:
            tag_count = random.randint(
                0,
                min(MAX_TAGS_PER_POST, len(tags)),
            )

            selected_tags = random.sample(
                tags,
                k=tag_count,
            )

            post.tags.set(selected_tags)

        return len(posts)

    def create_comments(self, count: int) -> int:
        if count == 0:
            return 0

        authors = list(User.objects.all())

        published_posts = list(
            Post.objects.filter(
                status=Post.Status.PUBLISHED
            )
        )

        if not authors:
            raise CommandError(
                "Cannot create comments without users."
            )

        if not published_posts:
            raise CommandError(
                "Cannot create comments without "
                "published posts."
            )

        comments = []

        for _ in range(count):
            sentence_count = random.randint(
                1,
                MAX_COMMENT_SENTENCES,
            )

            comments.append(
                Comment(
                    post=random.choice(
                        published_posts
                    ),
                    author=random.choice(authors),
                    body=fake.paragraph(
                        nb_sentences=sentence_count
                    ),
                )
            )

        Comment.objects.bulk_create(comments)

        return len(comments)

    def handle(
        self,
        *args: Any,
        **options: Any,
    ) -> None:
        start_time = time.perf_counter()

        users_count = options["users"]
        posts_count = options["posts"]
        comments_count = options["comments"]
        clear = options["clear"]

        counts = (
            users_count,
            posts_count,
            comments_count,
        )

        if any(count < 0 for count in counts):
            raise CommandError(
                "Number of objects cannot be negative."
            )

        with transaction.atomic():
            if clear:
                self.clear_data()

            available_users = (
                User.objects.count() + users_count
            )

            if (
                (posts_count > 0 or comments_count > 0)
                and available_users == 0
            ):
                raise CommandError(
                    "Cannot create posts or comments "
                    "without users."
                )

            created_users = self.create_users(
                users_count
            )

            created_categories = (
                self.create_categories()
            )

            created_tags = self.create_tags()

            created_posts = self.create_posts(
                posts_count
            )

            created_comments = self.create_comments(
                comments_count
            )

        elapsed = time.perf_counter() - start_time

        self.stdout.write(
            self.style.SUCCESS(
                f"Users:       {created_users} created\n"
                f"Categories:  {created_categories} created\n"
                f"Tags:        {created_tags} created\n"
                f"Posts:       {created_posts} created\n"
                f"Comments:    {created_comments} created\n"
                f"Done in {elapsed:.2f} seconds"
            )
        )
