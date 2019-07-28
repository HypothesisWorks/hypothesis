RELEASE_TYPE: patch

This patch changes an internal use of MD5 to SHA hashes, to better support
users subject to FIPS-140.  There is no user-visible or API change.

Thanks to Alex Gaynor for this patch.
