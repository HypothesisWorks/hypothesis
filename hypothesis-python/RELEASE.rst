RELEASE_TYPE: minor

This release ensures that tests which raise ``RecursionError`` are not
reported as flaky simply because we run them from different initial
stack depths (:issue:`2494`).
