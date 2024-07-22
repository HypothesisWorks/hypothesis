RELEASE_TYPE: patch

This patch addresses the issue of hypothesis potentially accessing
mocked ``time.perf_counter`` during test execution (:issue:`4051`).
