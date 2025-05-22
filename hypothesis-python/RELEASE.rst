RELEASE_TYPE: patch

This patch adds detection of GitLab CI environments in :func:`_settings.is_in_ci`.
If `GITLAB_CI` is set in the environment, the default Hypothesis settings
will be changed to the CI profile. This affects the `derandomize`, `deadline`,
`database`, `print_blob` settings as well as the `too_slow` healthcheck.

Thanks to Genevieve Mendoza for this contribution!
