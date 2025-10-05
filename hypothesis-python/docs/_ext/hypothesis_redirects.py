# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

# vendored from https://github.com/documatt/sphinx-reredirects under the MIT
# license, with thanks

# ruff: noqa: G004

import re
from collections.abc import Mapping, Sequence
from fnmatch import fnmatch
from pathlib import Path
from string import Template
from typing import Optional
from urllib.parse import urlparse

from sphinx.application import Sphinx
from sphinx.builders.linkcheck import CheckExternalLinksBuilder, Hyperlink
from sphinx.util import logging
from sphinx.util.osutil import SEP

OPTION_REDIRECTS = "redirects"
OPTION_REDIRECTS_DEFAULT: dict[str, str] = {}

OPTION_TEMPLATE_FILE = "redirect_html_template_file"
OPTION_TEMPLATE_FILE_DEFAULT = None

REDIRECT_FILE_DEFAULT_TEMPLATE = (
    '<html><head><meta http-equiv="refresh" content="0; url=${to_uri}"></head></html>'
)

logger = logging.getLogger(__name__)

wildcard_pattern = re.compile(r"[\*\?\[\]]")


def setup(app: Sphinx) -> dict:
    """
    Extension setup, called by Sphinx
    """
    app.connect("html-collect-pages", init)
    app.connect("builder-inited", collect_redirects_for_linkcheck)
    app.add_config_value(OPTION_REDIRECTS, OPTION_REDIRECTS_DEFAULT, "env")
    app.add_config_value(OPTION_TEMPLATE_FILE, OPTION_TEMPLATE_FILE_DEFAULT, "env")
    return {"parallel_read_safe": True}


def init(app: Sphinx) -> Optional[Sequence]:
    if not app.config[OPTION_REDIRECTS]:
        logger.debug("No redirects configured")
        return []

    rr = Reredirects(app)
    to_be_redirected = rr.grab_redirects()
    rr.create_redirects(to_be_redirected)

    # html-collect-pages requires to return iterable of pages to write,
    # we have no additional pages to write
    return []


class Reredirects:
    def __init__(self, app: Sphinx) -> None:
        self.app = app
        self.redirects_option: dict[str, str] = getattr(app.config, OPTION_REDIRECTS)
        self.template_file_option: str = getattr(app.config, OPTION_TEMPLATE_FILE)

    def grab_redirects(self) -> Mapping[str, str]:
        """Inspect redirects option in conf.py and returns dict mapping
        docname to target (with expanded placeholder)."""
        # docname-target dict
        to_be_redirected = {}

        # For each source-target redirect pair in conf.py
        for source, target in self.redirects_option.items():
            # no wildcard, append source as-is
            if not self._contains_wildcard(source):
                to_be_redirected[source] = target
                continue

            assert self.app.env

            # wildcarded source, expand to docnames
            expanded_docs = [
                doc for doc in self.app.env.found_docs if fnmatch(doc, source)
            ]

            if not expanded_docs:
                logger.warning(f"No documents match to '{source}' redirect.")
                continue

            for doc in expanded_docs:
                new_target = self._apply_placeholders(doc, target)
                to_be_redirected[doc] = new_target

        return to_be_redirected

    def docname_out_path(self, docname: str, suffix: str) -> Sequence[str]:
        """
        For a Sphinx docname (the path to a source document without suffix),
        returns path to outfile that would be created by the used builder.
        """
        # Return as-is, if the docname already has been passed with a suffix
        if docname.endswith(suffix):
            return [docname]

        # Remove any trailing slashes, except for "/"" index
        if len(docname) > 1 and docname.endswith(SEP):
            docname = docname.rstrip(SEP)

        # Figure out whether we have dirhtml builder
        out_uri = self.app.builder.get_target_uri(docname=docname)  # type: ignore

        if not out_uri.endswith(suffix):
            # If dirhtml builder is used, need to append "index"
            return [out_uri, "index"]

        # Otherwise, convert e.g. 'source' to 'source.html'
        return [out_uri]

    def create_redirects(self, to_be_redirected: Mapping[str, str]) -> None:
        """Create actual redirect file for each pair in passed mapping of
        docnames to targets."""

        # Corresponds to value of `html_file_suffix`, but takes into account
        # modifications done by the builder class
        try:
            suffix = self.app.builder.out_suffix  # type: ignore
        except Exception:
            suffix = ".html"

        for docname, target in to_be_redirected.items():
            out = self.docname_out_path(docname, suffix)
            redirect_file_abs = Path(self.app.outdir).joinpath(*out).with_suffix(suffix)

            redirect_file_rel = redirect_file_abs.relative_to(self.app.outdir)

            if redirect_file_abs.exists():
                logger.info(
                    f"Overwriting '{redirect_file_rel}' with redirect to '{target}'."
                )
            else:
                logger.info(f"Creating redirect '{redirect_file_rel}' to '{target}'.")

            self._create_redirect_file(redirect_file_abs, target)

    @staticmethod
    def _contains_wildcard(text: str) -> bool:
        """Tells whether passed argument contains wildcard characters."""
        return bool(wildcard_pattern.search(text))

    @staticmethod
    def _apply_placeholders(source: str, target: str) -> str:
        """Expand "source" placeholder in target and return it"""
        return Template(target).substitute({"source": source})

    def _create_redirect_file(self, at_path: Path, to_uri: str) -> None:
        """Actually create a redirect file according to redirect template"""

        content = self._render_redirect_template(to_uri)

        # create any missing parent folders
        at_path.parent.mkdir(parents=True, exist_ok=True)

        at_path.write_text(content, encoding="utf-8")

    def _render_redirect_template(self, to_uri: str) -> str:
        # HTML used as redirect file content
        redirect_template = REDIRECT_FILE_DEFAULT_TEMPLATE
        if self.template_file_option:
            redirect_file_abs = Path(self.app.srcdir, self.template_file_option)
            redirect_template = redirect_file_abs.read_text(encoding="utf-8")

        return Template(redirect_template).substitute({"to_uri": to_uri})


def collect_redirects_for_linkcheck(app):
    # Ignore when not invoked with linkcheck builder
    if not isinstance(app.builder, CheckExternalLinksBuilder):
        return

    redirects = Reredirects(app).grab_redirects()

    for docname, target in redirects.items():
        # Give a Sphinx or extensions change to modify original target URL
        if new_target := app.emit_firstresult("linkcheck-process-uri", target):
            target = new_target

        if urlparse(target).scheme not in ("http", "https"):
            # Checking redirects to other pages of the same documentation is not
            # supported for now.
            continue

        # Add target external URL to hyperlinks which linkcheck builder will check
        docpath = app.env.doc2path(docname)
        hyperlink = Hyperlink(uri=target, docname=docname, docpath=docpath, lineno=-1)
        app.builder.hyperlinks[target] = hyperlink
