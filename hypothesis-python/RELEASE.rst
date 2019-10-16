RELEASE_TYPE: patch

This patch changes a final internal use of MD5 to SHA384 hashes, to better
support users subject to FIPS-140. There is no user-visible or API change.
