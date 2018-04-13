RELEASE_TYPE: patch

This release fixes a somewhat obscure condition under which you could
occasionally see a failing test trigger an assertion error inside Hypothesis
instead of failing normally.
