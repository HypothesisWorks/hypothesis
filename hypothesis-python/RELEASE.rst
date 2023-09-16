RELEASE_TYPE: patch

This patch switches some of our type annotations to use :obj:`typing.Literal`
when only a few specific values are allowed, such as UUID or IP address versions.
