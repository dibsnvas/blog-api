from decouple import config
BLOG_secret_key = config('BLOG_ENV_SECRET_KEY')
BLOG_ENV_ID = config('BLOG_ENV_ID', default='local')
