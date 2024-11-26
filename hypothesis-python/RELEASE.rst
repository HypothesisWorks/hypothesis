RELEASE_TYPE: minor

* This release changes our input distribution for low ``max_examples``. Previously, we capped the size of inputs when generating at least the first 10 inputs, with the reasoning that early inputs to a property should be small. However, this meant properties with ``max_examples=10`` would consistent entirely of small inputs. This patch removes the hard lower bound so that inputs to these properties are more representative of the input space.
* When a user requests an interactive input via ``strategy.example``, we generate and cache a batch of 100 inputs, returning the first one. This can be expensive for large strategies or when only a few examples are needed. This release improves the speed of ``strategy.example`` by lowering the batch size to 10.
