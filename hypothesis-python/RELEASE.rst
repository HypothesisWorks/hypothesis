RELEASE_TYPE: patch

Fix a recursion error when :ref:`observability <observability>` is enabled and a test generates an object with a recursive reference, like ``a = []; a.append(a)``.
