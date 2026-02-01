RELEASE_TYPE: patch

This patch teaches our pytest plugin to :ref:` find interesting constants <v6.131.1>`
when pytest is collecting tests, to avoid arbitrarily attributing the latency
to whichever test function happened to be executed first (:issue:`4627`).
