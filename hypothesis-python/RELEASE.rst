RELEASE_TYPE: patch

When a user requests an interactive input via ``strategy.example``, we generate and cache a batch of 100 inputs and return the first one. As this initial batch can be expensive for large strategies, this patch reduces the batch size to 10.
