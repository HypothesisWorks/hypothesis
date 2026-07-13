# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hypothesistooling.cargo import write_version

if len(sys.argv) != 2:
    sys.exit(f"usage: {sys.argv[0]} <new_version>")

repo_root = Path(__file__).resolve().parent.parent.parent
write_version(repo_root / "hypothesis" / "rust" / "Cargo.toml", sys.argv[1])
