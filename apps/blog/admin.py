from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Category, Comment, Post, Tag


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Post)
class PostAdmin(ModelAdmin):
    list_display = ("title", "author", "status", "created_at")
    list_filter = ("status", "category")
    list_select_related = ("author",)
    search_fields = ("title", "author__email")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ("post", "author", "created_at")
    list_select_related = ("post", "author")
    search_fields = ("body",)
