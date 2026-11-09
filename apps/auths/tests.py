from django.test import TestCase
from django.urls import reverse

from .models import User


class UserAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            password="AdminPass123!",
        )
        self.client.force_login(self.admin)

    def test_admin_pages_open(self):
        for url in (
            reverse("admin:auths_user_changelist"),
            reverse("admin:auths_user_add"),
            reverse("admin:auths_user_change", args=[self.admin.pk]),
            reverse("admin:blog_post_add"),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_user_created_in_admin_has_hashed_password(self):
        response = self.client.post(
            reverse("admin:auths_user_add"),
            {
                "email": "New.User@Example.com",
                "first_name": "New",
                "last_name": "User",
                "password1": "S3cret-pass-42",
                "password2": "S3cret-pass-42",
            },
        )
        self.assertEqual(response.status_code, 302)

        user = User.objects.get(email="new.user@example.com")
        self.assertNotEqual(user.password, "S3cret-pass-42")
        self.assertTrue(user.check_password("S3cret-pass-42"))
