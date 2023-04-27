RELEASE_TYPE: patch

This patch updates our minimum Numpy version to 1.16, and restores compatibility
with versions before 1.20, which were broken by a mistake in Hypothesis 6.72.4
(:issue:`3625`).
