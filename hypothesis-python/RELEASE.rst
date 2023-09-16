RELEASE_TYPE: patch

This patch improves the documentation of :obj:`@example(...).xfail() <hypothesis.example.xfail>`
by adding a note about :pep:`614`, similar to :obj:`@example(...).via() <hypothesis.example.via>`,
and adds a warning when a strategy generates a test case which seems identical to
one provided by an xfailed example.
