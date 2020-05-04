RELEASE_TYPE: patch

If you have :pypi:`django` installed but don't use it, this patch will make
``import hypothesis`` a few hundred milliseconds faster (e.g. 0.704s -> 0.271s).

Thanks to :pypi:`importtime-waterfall` for highlighting this problem and
`Jake Vanderplas <https://twitter.com/jakevdp/status/1130983439862181888>`__ for
the solution - it's impossible to misuse code from a module you haven't imported!
