RELEASE_TYPE: patch

Fix a remaining thread-safety issue with the recursion limit warning Hypothesis issues when an outside caller sets ``sys.setrecursionlimit`` (see :ref:`v6.135.23`).
