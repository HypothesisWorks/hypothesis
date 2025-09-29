# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.


SITENAME = AUTHOR = "Hypothesis"
SITESUBTITLE = "The property-based testing library for Python"
# SITEURL = "https://hypothesis.works"

PATH = "content"
TIMEZONE = "UTC"
DELETE_OUTPUT_DIRECTORY = True

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

CATEGORY_URL = "articles/"
CATEGORY_SAVE_AS = "articles/index.html"

FILENAME_METADATA = r"(?P<date>\d{4}-\d{2}-\d{2})-(?P<slug>.+)"

THEME = "./theme/"
STATIC_PATHS = [
    "images",
    "../../brand/favicon.ico",
    "../../brand/dragonfly-rainbow.svg",
]
EXTRA_PATH_METADATA = {
    "../../brand/favicon.ico": {"path": "favicon.ico"},
    "../../brand/dragonfly-rainbow.svg": {"path": "dragonfly-rainbow.svg"},
}
PROFILE_IMAGE_URL = "/dragonfly-rainbow.svg"

MENUITEMS = (
    ("Blog", "/articles"),
    ("Documentation", "https://hypothesis.readthedocs.io/en/latest/"),
    ("GitHub", "https://github.com/HypothesisWorks/hypothesis/"),
)

DEFAULT_PAGINATION = False

# same as the default from https://docs.getpelican.com/en/latest/settings.html#MARKDOWN,
# but with use_pygments = False, since we use prism.js for syntax highlighting
# instead.
MARKDOWN = {
    "extension_configs": {
        "markdown.extensions.codehilite": {
            "use_pygments": False,
            "css_class": "highlight",
        },
        "markdown.extensions.extra": {},
        "markdown.extensions.meta": {},
    },
    "output_format": "html5",
}

# Uncomment following line if you want document-relative URLs when developing
# RELATIVE_URLS = True
