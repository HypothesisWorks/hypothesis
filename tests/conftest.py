# coding=utf-8

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import print_function, unicode_literals

# END HEADER

import hypothesis.settings

hypothesis.settings.default.max_examples = 1000
hypothesis.settings.default.timeout = -1

try:
    import resource
    MAX_MEMORY = 10
    resource.setrlimit(resource.RLIMIT_DATA, (MAX_MEMORY, MAX_MEMORY))
except ImportError:
    pass
