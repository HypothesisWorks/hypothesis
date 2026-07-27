# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import pathlib
import sysconfig

# See https://coverage.readthedocs.io/en/latest/subprocess.html for details

pathlib.Path(sysconfig.get_path("purelib"), "coverage_subprocess.pth").write_text(
    "import coverage; coverage.process_startup()\n", encoding="utf-8"
)
