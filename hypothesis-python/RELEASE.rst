RELEASE_TYPE: patch

This patch changes the priority order of pretty printing logic so that a user
provided pretty printing method will always be used in preference to e.g.
printing it like a dataclass.
