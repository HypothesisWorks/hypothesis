RELEASE_TYPE: patch

This patch fixes a bug where generating a unique collection of non-empty
collections could fail the :obj:`~hypothesis.HealthCheck.large_base_example`
health check, because the zero-data probe did not terminate (:issue:`4918`).

Thanks to @eric-weaver for the detailed report, and to @agustin18 for this fix!
