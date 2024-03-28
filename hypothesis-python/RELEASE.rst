RELEASE_TYPE: patch

This release suppresses flakiness reporting for a very mild form of flakiness
where two exception groups being raised in different iterations of the test
differ only in the number of times that their constituent exceptions are
raised. This is an essentially harmless form of flakiness that can be hard
to avoid in certain scenarios.
