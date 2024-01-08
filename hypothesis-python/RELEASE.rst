RELEASE_TYPE: patch

This patch registers explicit strategies for a handful of builtin types,
motivated by improved introspection in PyPy 7.3.14 triggering existing
internal warnings.
Thanks to Carl Friedrich Bolz-Tereick for helping us work out what changed!
