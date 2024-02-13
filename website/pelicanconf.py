AUTHOR = "Hypothesis developers"
SITENAME = "Hypothesis"
SITEURL = ""

PATH = "content"

TIMEZONE = "UTC"

DEFAULT_LANG = "en"

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

ARTICLE_URL = "{category}/{slug}/"
ARTICLE_SAVE_AS = "{category}/{slug}/index.html"
DEFAULT_CATEGORY = "articles"
DISPLAY_PAGES_ON_MENU = False

FILENAME_METADATA = "(?P<date>\d{4}-\d{2}-\d{2})-(?P<slug>.+)"

STATIC_PATHS = ["../../brand/favicon.ico"]
EXTRA_PATH_METADATA = {
    "../../brand/favicon.ico": {"path": "favicon.ico"},
}

MENUITEMS = (
    ("Documentation", "https://hypothesis.readthedocs.io/en/latest/"),
    ("GitHub repo", "https://github.com/HypothesisWorks/hypothesis/"),
    ("PyPI", "https://pypi.org/project/hypothesis/"),
)

# Blogroll
# LINKS = (
#     ("Pelican", "https://getpelican.com/"),
#     ("Python.org", "https://www.python.org/"),
#     ("Jinja2", "https://palletsprojects.com/p/jinja/"),
#     ("You can modify those links in your config file", "#"),
# )

# Social widget
# SOCIAL = (
#     ("You can add links in your config file", "#"),
#     ("Another social link", "#"),
# )

DEFAULT_PAGINATION = False

# Uncomment following line if you want document-relative URLs when developing
# RELATIVE_URLS = True
