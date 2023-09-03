RELEASE_TYPE: patch

Disable all health checks during replay of db examples, so that we
don't produce spurious failures when there are db-key collisions.
Also adds a health check to detect one source of such collisions.
