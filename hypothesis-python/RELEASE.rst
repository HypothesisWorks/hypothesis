RELEASE_TYPE: patch

This patch ensures that the :ref:`hypothesis codemod <codemods>` CLI
will print a warning instead of stopping with an internal error if
one of your files contains invalid syntax (:issue:`3759`).
