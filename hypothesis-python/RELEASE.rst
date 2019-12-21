RELEASE_TYPE: patch

This release fixes a small internal bug in shrinking which could have caused it
to perform slightly more tests than were necessary. Fixing this shouldn't have
much effect but it will make shrinking slightly faster.
