RELEASE_TYPE: patch

This patch makes some small changes to our NumPy integration to ensure forward
compatibility. Also, ``numpy.lib.function_base._parse_gufunc_signature`` tests
were removed as this API is considered stable.

Thanks to Mateusz Sokół for :pull:`3761`.
