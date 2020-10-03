RELEASE_TYPE: minor

This release adds a new :class:`~hypothesis.extra.redis.RedisExampleDatabase`,
along with the :class:`~hypothesis.database.ReadOnlyDatabase`
and :class:`~hypothesis.database.MultiplexedDatabase` helpers, to support
team workflows where failing examples can be seamlessly shared between everyone
on the team - and your CI servers or buildbots.
