# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import re
from pathlib import Path

import hypothesistooling as tools


def test_dataclass_lint():
    # lint each dataclass and assert each has a frozen= and slots= parameter.
    # see https://github.com/HypothesisWorks/hypothesis/pull/4577#discussion_r2480402510
    pattern = re.compile(r"^@dataclass.*$", re.MULTILINE)

    for path in tools.all_files():
        if path.suffix != ".py":
            continue
        if path.name.startswith("test_"):
            continue

        content = Path(path).read_text(encoding="utf-8")
        for match in pattern.findall(content):
            if not ("frozen=" in match and "slots=" in match):
                raise ValueError(
                    f"@dataclass in {path} does not explicitly set both frozen= "
                    "and slots=."
                )
