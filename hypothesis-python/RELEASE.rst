RELEASE_TYPE: patch

This patch defers creation of the ``.hypothesis`` directory until we have
something to store in it, meaning that it will appear when Hypothesis is
used rather than simply installed.

Thanks to Peter C Kroon for the Hacktoberfest patch!
