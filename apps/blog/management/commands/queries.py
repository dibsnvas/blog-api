from datetime import timedelta
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection 
from django.db.models import Count, QuerySet
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.blog.models import Post
from apps.blog.queries import QUERIES

PREVIEW_ROWS = 5
WRITE_QUERIES = {40, 41, 42, 43, 44}
LAST_DAYS = 30
MIN_TAG_POSTS = 15
FULL_NAME_PREFIX = 3

class Command(BaseCommand):
    help = 'Run the ORM queries from apps/blog/queries.py'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--number",
            type=int,
            help = "Run only the query with this number",
        )
        parser.add_argument(
            "--sql",
            action = "store_true",
            help="Also print the SQL sent to the database",
        )


    def build_arguments(self) -> dict[int, dict[str,Any]]:
        post = Post.objects.select_related("author").first()
        if post is None:
            raise CommandError("No posts. Run: python manage.py seed")

        tagged_post = (
            Post.objects.annotate(tag_count=Count("tags"))
            .filter(tag_count__gte=2)
            .first()
        )
        if tagged_post is None:
            raise CommandError("No post with two tags. Run seed again.")
        first_tag, second_tag = tagged_post.tags.values_list(
            "slug", flat=True
        )[:2]

        author = post.author
        word = post.title.split()[0]
        today = timezone.localdate()

        return {
            4: {"slug": post.slug},
            7: {"page": 1},
            8: {"word": word},
            9: {"domain": "example.com"},
            11: {"slugs": ["python", "django"]},
            12: {"year": today.year, "month": today.month},
            13: {"days":LAST_DAYS},
            14: {"start": today - timedelta(days=LAST_DAYS), "end": today},
            15: {"email": author.email},
            16: {"tag_slug": "api"},
            17: {"category_slug": "python"},
            21: {"first_slug": first_tag, "second_slug": second_tag},
            22: {"text": word},
            34: {"min_posts": MIN_TAG_POSTS},
            37: {
                "text": (
                    f"{author.first_name} "
                    f"{author.last_name[:FULL_NAME_PREFIX]}"
                
                ).lower()
            },
            40: {"name": "Django ORM"},
            41: {"days": LAST_DAYS},
            42: {"category_slug": "python", "tag_slug": "orm"},
            43: {"source_slug": "frontend", "target_slug": "backend"},
        }
    def handle(self, *args: Any, **options: Any) -> None:
        number = options["number"]

        if number is None:
            numbers = [n for n in QUERIES if n not in WRITE_QUERIES]
        elif number in QUERIES:
            numbers = [number]
        else:
            raise CommandError(f"Query #{number} does not exist.")

        arguments = self.build_arguments()

        for query_number in numbers:
            self.run_query(
                query_number,
                arguments.get(query_number, {}),
                options["sql"],
            )
    
    def run_query(
        self,
        number: int,
        arguments: dict[str, Any],
        show_sql: bool,
    ) -> None:
        function = QUERIES[number]
        annotations: list[str] = []

        with CaptureQueriesContext(connection) as context:
            try:
                result = function(**arguments)
            except ObjectDoesNotExist as error:
                raise CommandError(
                    f"{error} Run: python manage.py seed --clear"
                ) from error
            if isinstance(result, QuerySet):
                annotations = list(result.query.annotations)
                result = list(result)
        count = len(context.captured_queries)
        word = "query" if count == 1 else "queries"
        self.stdout.write(f"#{number} {function.__name__} — {count} SQL {word}")

        if show_sql:
            for query in context.captured_queries:
                self.stdout.write(query["sql"])
        
        self.write_result(result, annotations)

    def write_result(self, result: Any, annotations: list[str]) -> None:
        if isinstance(result, dict):
            result = [f"{key}: {value}" for key, value in result.items()]

        if not isinstance(result, list):
            self.stdout.write(f" {result}")
            return

        for row in result[:PREVIEW_ROWS]:
            if annotations:
                values = {name: getattr(row, name) for name in annotations}
                self.stdout.write(f" {row} {values}")
            else:
                self.stdout.write(f" {row}")

        self.stdout.write(f" ({len(result)} rows)")