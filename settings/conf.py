from decouple import Csv, config

BLOG_ENV_ID = config("BLOG_ENV_ID", default="local")
BLOG_SECRET_KEY = config("BLOG_ENV_SECRET_KEY")
BLOG_DEBUG = config("BLOG_ENV_DEBUG", default=False, cast=bool)
BLOG_ALLOWED_HOSTS = config("BLOG_ENV_ALLOWED_HOSTS", default="", cast=Csv())
