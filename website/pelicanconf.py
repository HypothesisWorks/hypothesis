# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from os.path import basename

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

# Disable the default archives page
ARCHIVES_SAVE_AS = ""

FILENAME_METADATA = r"(?P<date>\d{4}-\d{2}-\d{2})-(?P<slug>.+)"

THEME = "./theme/"
STATIC_PATHS = [
    "../../brand/favicon.ico",
    "../../brand/dragonfly-rainbow.svg",
    "../archive-redirect.html",
]
EXTRA_PATH_METADATA = {k: {"path": basename(k)} for k in STATIC_PATHS}
EXTRA_PATH_METADATA["../archive-redirect.html"] = {"path": "archives.html"}
PROFILE_IMAGE_URL = "/dragonfly-rainbow.svg"

MENUITEMS = (
    ("Blog", "/articles"),
    ("Docs", "https://hypothesis.readthedocs.io/en/latest/"),
    ("GitHub", "https://github.com/HypothesisWorks/hypothesis/"),
    ("PyPI", "https://pypi.org/project/hypothesis/"),
)

# Author information - map from short alias to full name and URL
AUTHOR_NAMES = {
    "alexwlchan": "Alex Chan",
    "carlini": "Nicholas Carlini",
    "drmaciver": "David R. MacIver",
    "giorgiosironi": "Giorgio Sironi",
    "hwayne": "Hillel Wayne",
    "jml": "Jonathan M. Lange",
    "liam": "Liam DeVoe",
    "maaz": "Muhammad Maaz",
    "nchammas": "Nicholas Chammas",
    "zac-hd": "Zac Hatfield-Dodds",
}

AUTHOR_URLS = {
    "alexwlchan": "https://alexwlchan.net",
    "carlini": "https://nicholas.carlini.com/",
    "drmaciver": "http://www.drmaciver.com",
    "giorgiosironi": "http://giorgiosironi.com",
    "hwayne": "https://www.hillelwayne.com/",
    "jml": "https://jml.io",
    "liam": "https://tybug.dev",
    "maaz": "https://www.mmaaz.ca/",
    "nchammas": "http://nchammas.com",
    "zac-hd": "https://zhd.dev",
}
assert set(AUTHOR_URLS).issubset(AUTHOR_NAMES)

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
