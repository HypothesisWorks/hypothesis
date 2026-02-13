RELEASE_TYPE: patch

This patch fixes a crash when :obj:`sys.modules` contains unhashable values,
such as ``types.SimpleNamespace`` objects (:issue:`4660`).
