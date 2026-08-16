# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""
Client-side redirects. Configured via the ``redirects`` dict in conf.py:

    redirects = {
        "dead-page": "new-page#section",
        "dead-page#old-anchor": "other-page#new-anchor",
        "live-page#moved-anchor": "other-page#new-anchor",
    }

Both keys and values should not include `.html`. If the old page does not exist, we create
a stub html file at that location which redirects to the redirect target. If the old page
exists, we inject a script into that page at build time that handles the redirect.

Here is the semantics of the redirection mapping (assuming the config above):

    user visits                  redirected to
    ---------------------------  ---------------------------
    dead-page.html               new-page.html#section
    dead-page.html#old-anchor    other-page.html#new-anchor
    dead-page.html#surviving-id  new-page.html#surviving-id

    dead-page.html#gone          new-page.html#section
    live-page.html#present-id    no redirect
    live-page.html#moved-anchor  other-page.html#new-anchor
    live-page.html#gone          no redirect

The particular case we care about here is dead-page.html#surviving-id ->
new-page.html#surviving-id. If we redirected dead-page.html#surviving-id ->
new-page#section unconditionally, we would miss automatically covering many valid
redirects. We instead compute the existing anchors on the redirect target and use that
to decide where to redirect an anchor on a dead page, depending on if that anchor still
exists or not.
"""

import json
from string import Template

from docutils import nodes
from sphinx.application import Sphinx
from sphinx.environment import BuildEnvironment
from sphinx.util import logging

logger = logging.getLogger(__name__)

_STUB_TEMPLATE = Template("""\
<!DOCTYPE html>
<html>
  <head>
    <noscript>
      <meta http-equiv="refresh" content="0; url=$target" />
    </noscript>
    <script>
      // fragment -> href of the anchor's new location
      var anchorMap = $anchor_map;
      // ids which exist on the target page
      var targetIds = $target_ids;
      var target = "$target";

      var fragment;
      try {
        fragment = decodeURIComponent(window.location.hash.slice(1));
      } catch (e) {
        fragment = "";
      }
      var destination;
      if (Object.prototype.hasOwnProperty.call(anchorMap, fragment)) {
        destination = anchorMap[fragment];
      } else if (targetIds.indexOf(fragment) !== -1) {
        destination = target.split("#")[0] + "#" + fragment;
      } else {
        destination = target;
      }
      window.location.replace(destination);
    </script>
  </head>
</html>
""")

_LIVE_PAGE_TEMPLATE = Template("""\
<script>
  (function () {
    // fragment -> href of the anchor's new location
    var anchorMap = $anchor_map;
    function redirectMovedAnchor() {
      var fragment;
      try {
        fragment = decodeURIComponent(window.location.hash.slice(1));
      } catch (e) {
        return;
      }
      if (
        fragment &&
        !document.getElementById(fragment) &&
        Object.prototype.hasOwnProperty.call(anchorMap, fragment)
      ) {
        window.location.replace(anchorMap[fragment]);
      }
    }
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", redirectMovedAnchor);
    } else {
      redirectMovedAnchor();
    }
  })();
</script>
""")


def setup(app: Sphinx) -> dict:
    app.add_config_value("redirects", {}, "env")
    app.connect("env-check-consistency", validate_redirects)
    app.connect("html-page-context", inject_live_page_script)
    app.connect("html-collect-pages", write_stubs)
    return {"parallel_read_safe": True, "parallel_write_safe": True}


def _parse(entry: str) -> tuple[str, str | None]:
    """Split a "docname" or "docname#fragment" config string"""
    assert ".html" not in entry
    assert not entry.startswith("/")
    assert not entry.endswith("/")
    docname, sep, fragment = entry.partition("#")
    assert docname
    assert not sep or fragment
    assert "#" not in fragment
    return docname, fragment or None


class Redirects:
    """The parsed and validated redirect config for one build."""

    def __init__(self, app: Sphinx) -> None:
        self.app = app
        self.env = app.env
        self._ids_cache: dict[str, set[str]] = {}
        # docname -> (target docname, target fragment or None)
        self.pages: dict[str, tuple[str, str | None]] = {}
        # (docname, fragment) -> (target docname, target fragment or None)
        self.anchors: dict[tuple[str, str], tuple[str, str | None]] = {}

        for source, target in app.config.redirects.items():
            source_doc, source_fragment = _parse(source)
            parsed_target = _parse(target)
            if source_fragment is None:
                self.pages[source_doc] = parsed_target
            else:
                self.anchors[source_doc, source_fragment] = parsed_target

    def page_ids(self, docname: str) -> set[str]:
        """All ids which exist on a (live) page, from its doctree."""
        if docname not in self._ids_cache:
            ids: set[str] = set()
            for node in self.env.get_doctree(docname).findall(nodes.Element):
                ids.update(node["ids"])
            self._ids_cache[docname] = ids
        return self._ids_cache[docname]

    def validate(self) -> None:
        for source_doc, target in self.pages.items():
            # the stub would shadow the real page
            assert source_doc not in self.env.found_docs
            self._validate_target(target)

        for (source_doc, source_fragment), target in self.anchors.items():
            if source_doc in self.env.found_docs:
                # the redirect would never fire if the anchor still exists
                assert source_fragment not in self.page_ids(source_doc)
            else:
                # a dead page needs a page redirect to serve its anchor redirects
                assert source_doc in self.pages
            self._validate_target(target)

    def _validate_target(self, target: tuple[str, str | None]) -> None:
        target_doc, target_fragment = target
        assert target_doc in self.env.found_docs
        if target_fragment is not None:
            assert target_fragment in self.page_ids(target_doc)

    def href(self, from_docname: str, target: tuple[str, str | None]) -> str:
        """Relative URL from a page to a target."""
        target_doc, target_fragment = target
        uri = self.app.builder.get_relative_uri(from_docname, target_doc)
        if target_fragment is not None:
            uri += f"#{target_fragment}"
        return uri

    def anchor_map(self, docname: str) -> dict[str, str]:
        """fragment -> href, for anchor entries whose source is ``docname``."""
        return {
            fragment: self.href(docname, target)
            for (doc, fragment), target in self.anchors.items()
            if doc == docname
        }


def _get_redirects(app: Sphinx) -> "Redirects":
    # env-check-consistency is skipped on incremental builds with no outdated
    # docs, so each event lazily constructs and validates on first use.
    if getattr(app, "_hypothesis_redirects", None) is None:
        app._hypothesis_redirects = Redirects(app)  # type: ignore
        app._hypothesis_redirects.validate()  # type: ignore
    return app._hypothesis_redirects  # type: ignore


def validate_redirects(app: Sphinx, env: BuildEnvironment) -> None:
    _get_redirects(app)


def inject_live_page_script(
    app: Sphinx, pagename: str, templatename: str, context: dict, doctree
) -> None:
    # only redirect on the standalone html builder, not e.g. epub or singlehtml
    if app.builder.name != "html":
        return
    anchor_map = _get_redirects(app).anchor_map(pagename)
    if anchor_map:
        script = _LIVE_PAGE_TEMPLATE.substitute(
            anchor_map=json.dumps(anchor_map, sort_keys=True)
        )
        context["metatags"] += script


def write_stubs(app: Sphinx):
    if app.builder.name != "html":
        return []
    redirects = _get_redirects(app)
    for source_doc, target in sorted(redirects.pages.items()):
        target_doc, _ = target
        stub = _STUB_TEMPLATE.substitute(
            target=redirects.href(source_doc, target),
            anchor_map=json.dumps(redirects.anchor_map(source_doc), sort_keys=True),
            target_ids=json.dumps(sorted(redirects.page_ids(target_doc))),
        )
        path = (app.outdir / source_doc).with_suffix(app.builder.out_suffix)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(stub, encoding="utf-8")
        logger.info("writing redirect stub %r", source_doc)
    return []
