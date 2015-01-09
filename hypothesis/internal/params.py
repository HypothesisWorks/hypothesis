import collections
import hypothesis.internal.utils.distributions as dist
import inspect


class Parameter(object):
    def __init__(self):
        pass

    def draw(self, random):
        raise NotImplemented()

    def redraw(self, random, value):
        return self.draw(random)


class GeometricParameter(Parameter):
    def __init__(self, p):
        Parameter.__init__(self)
        if not (0 < p < 1):
            raise ValueError("Value %f out of valid range (0, 1)" % (p,))
        self.p = p

    def draw(self, random):
        return dist.geometric(random, self.p)


class UniformIntegerParameter(Parameter):
    def __init__(self, lower_bound, upper_bound):
        Parameter.__init__(self)
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

    def draw(self, random):
        return random.randint(self.lower_bound, self.upper_bound)


class ExponentialParameter(Parameter):
    def __init__(self, mean):
        Parameter.__init__(self)
        if mean <= 0:
            raise ValueError(
                "Invalid mean %f for exponential distribution" % (mean,))
        self.lambd = 1.0 / mean

    def draw(self, random):
        return random.expovariate(self.lambd)


class UniformFloatParameter(Parameter):
    def __init__(self, lower_bound, upper_bound):
        Parameter.__init__(self)
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

    def draw(self, random):
        return self.lower_bound + (
            self.upper_bound - self.lower_bound
        ) * random.random()


class NormalParameter(Parameter):
    def __init__(self, mean, variance):
        self.mean = mean
        self.sd = variance ** 0.5

    def draw(self, random):
        return random.normalvariate(self.mean, self.sd)


class GammaParameter(Parameter):
    def __init__(self, alpha, beta):
        self.alpha = alpha
        self.beta = beta

    def draw(self, random):
        return random.gammavariate(self.alpha, self.beta)


class NonEmptySubset(Parameter):
    def __init__(self, elements):
        self.elements = tuple(elements)
        if not elements:
            raise ValueError("Must have at least one element")
        # TODO: This should have a more principled choice. It seesm to be good
        # in practice though.
        desired_expected_value = 1.0 if len(elements) <= 3 else 2.0
        self.p = desired_expected_value / len(elements)

    def draw(self, random):
        if len(self.elements) == 1:
            return self.elements[0]
        result = []
        while not result:
            result = [
                x for x in self.elements if dist.biased_coin(random, self.p)
            ]
        return result


class BiasedCoin(Parameter):
    def __init__(self, p):
        Parameter.__init__(self)
        if not (0 < p < 1):
            raise ValueError("Value %f out of valid range (0, 1)" % (p,))
        self.p = p

    def draw(self, random):
        return dist.biased_coin(random, self.p)


class CompositeParameter(Parameter):
    def __init__(self, *args, **kwargs):
        Parameter.__init__(self)
        if not kwargs and len(args) == 1 and inspect.isgenerator(args[0]):
            args = tuple(args[0])
        is_pure_tuple = not kwargs
        children = []
        for i, x in enumerate(args):
            name = "arg%d" % (i,)
            if name in kwargs:
                raise ValueError("Duplicate parameter name %s" % (name,))
            if hasattr(self, name):
                raise ValueError("Invalid parameter name %s" % (name,))
            kwargs[name] = x
            children.append(name)

        for k, v in sorted(kwargs.items()):
            if k not in children:
                children.append(k)
            setattr(self, k, v)
        self.children = tuple(children)
        if is_pure_tuple:
            self.Result = tuple
        else:
            self.Result = collections.namedtuple('Result', self.children)

    def __repr__(self):
        return "CompositeParameter(%s)" % (', '.join(
            "%s=%r" % (name, getattr(self, name))
            for name in self.children
        ))

    def draw(self, random):
        bits = [
            getattr(self, c).draw(random) for c in self.children
        ]
        if self.Result == tuple:
            return tuple(bits)
        else:
            return self.Result(*bits)
