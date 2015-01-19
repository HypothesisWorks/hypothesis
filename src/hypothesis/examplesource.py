from random import Random


class ExampleSource(object):
    """
    An object that provides you with an a stream of examples to work with.

    Starts by fetching examples from storage if storage has been provided but
    if storage is None will happily continue without. Follows by generating new
    examples, but if the strategy is None then will stop there. Must have at
    least one of strategy and storage but does not have to have both.

    This does not handle deduplication or make decisions as to when to stop.
    That's up to the caller.
    """
    def __init__(self, random, strategy, storage, min_parameters=100):
        if not isinstance(random, Random):
            raise ValueError("A Random is required but got %r" % (random,))
        if strategy is None and storage is None:
            raise ValueError(
                "Cannot proceed without at least one way of getting examples"
            )
        self.strategy = strategy
        self.storage = storage
        self.random = random
        self.parameters = []
        self.last_parameter_index = -1
        self.min_parameters = min_parameters
        self.bad_counts = []

    def mark_bad(self):
        """
        The last example was bad. If possible can we have less of that please?
        """
        if self.last_parameter_index < 0:
            return
        while len(self.bad_counts) <= self.last_parameter_index:
            self.bad_counts.append(0)
        self.bad_counts[self.last_parameter_index] += 1

    def new_parameter(self):
        result = self.strategy.parameter.draw(self.random)
        self.parameters.append(result)
        return result

    def pick_a_parameter(self):
        if len(self.parameters) < self.min_parameters:
            return self.new_parameter()
        else:
            self.last_parameter_index = self.random.randint(
                0, len(self.parameters) - 1
            )
            return self.parameters[self.last_parameter_index]

    def __iter__(self):
        if self.storage is not None:
            for example in self.storage.fetch():
                yield example

        if self.strategy is not None:
            while True:
                parameter = self.pick_a_parameter()
                yield self.strategy.produce(
                    self.random, parameter
                )
