# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

from hypothesis.database import (
    DirectoryBasedExampleDatabase,
    InMemoryExampleDatabase,
    MultiplexedDatabase,
)

from tests.common.utils import skipif_threading

# trivial covering tests as a stopgap while we skip our proper database listener
# tests. Can be removed when we re-enable those.


@skipif_threading
def test_start_stop_multiplexed_listener(tmp_path):
    db = MultiplexedDatabase(
        InMemoryExampleDatabase(), DirectoryBasedExampleDatabase(tmp_path)
    )
    listener = lambda event: None
    db.add_listener(listener)
    db.remove_listener(listener)


@skipif_threading
def test_start_stop_directory_listener(tmp_path):
    db = DirectoryBasedExampleDatabase(tmp_path)
    listener = lambda event: None
    db.add_listener(listener)
    db.remove_listener(listener)
