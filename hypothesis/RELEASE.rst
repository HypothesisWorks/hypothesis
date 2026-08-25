RELEASE_TYPE: minor

Test case observations from |observability| now give more detail about why a
test case failed or was abandoned (:issue:`3845`). ``metadata`` includes a new
``status_reason_location`` key: a ``filename:lineno`` location for the
``status_reason``, if known - for example the location of a failing |assume|
call, the |.filter| call whose predicate rejected the last drawn value, or the
exception for failing tests.

Test cases which exceeded the maximum allowed size now also report a nonempty
``status_reason``.
