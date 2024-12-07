# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import sphinx
from sphinx.application import Sphinx
from sphinx.builders.linkcheck import HyperlinkAvailabilityChecker

# We want to customize the linkcheck behavior so that references from intersphinx
# mappings are not checked. We use these liberally and don't want to spend CI time
# checking their validity. If it's in an inventory, sphinx should guarantee
# it's valid, sans very weird things happening.
#
# Sphinx splits the link check logic across a CheckExternalLinksBuilder builder
# and a HyperlinkCollector post_transform (and a HyperlinkAvailabilityChecker
# helper class). There are various points in each where we could add this
# ignore-intersphinx hook.
#
# Monkey-patching HyperlinkAvailabilityChecker isn't great, but is the best way
# I found to go about this.

# set by on_builder_inited
inventories = {}


def is_intersphinx_link(uri):
    for inventory in inventories.values():
        uris = {uri for _name, _version, uri, _display_name in inventory.values()}
        if uri in uris:
            return True
    return False


class HypothesisLinkChecker(HyperlinkAvailabilityChecker):
    def is_ignored_uri(self, uri: str) -> bool:
        if is_intersphinx_link(uri):
            return True
        return super().is_ignored_uri(uri)


sphinx.builders.linkcheck.HyperlinkAvailabilityChecker = HypothesisLinkChecker


# Hook the builder to get access to the intersphinx inventory. app.env is not
# available in setup()
def on_builder_inited(app: Sphinx) -> None:
    global inventories
    inventories = getattr(app.env, "intersphinx_inventory", {})


def setup(app: Sphinx):
    app.connect("builder-inited", on_builder_inited)
