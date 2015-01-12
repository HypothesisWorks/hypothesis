import collections
import hypothesis.internal.utils.distributions as dist
import inspect


class Parameter(object):
    def __init__(self):
        pass

    def draw(self, random):
        raise NotImplemented()  # pragma: no cover


class ExponentialParameter(Parameter):
    def __init__(self, lambd):
        Parameter.__init__(self)
        if lambd <= 0:
            raise ValueError(
                "Invalid lambda %f for exponential distribution" % (lambd,))
        self.lambd = lambd

    def draw(self, random):
        return random.expovariate(self.lambd)


class BetaFloatParameter(Parameter):
    def __init__(self, alpha, beta):
        self.alpha = alpha
        self.beta = beta

    def draw(self, random):
        return random.betavariate(alpha=self.alpha, beta=self.beta)


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
    def __init__(self, elements, activation_chance=None):
        self.elements = tuple(elements)
        if not elements:
            raise ValueError("Must have at least one element")
        if activation_chance is None:
            # TODO: This should have a more principled choice. It seems to be
            # good in practice though.
            # Note: The actual expected value is slightly higher because we're
            # conditioning on the result being non-empty.
            desired_expected_value = 1.0 if len(elements) <= 3 else 2.0
            activation_chance = desired_expected_value / len(elements)
        self.p = activation_chance

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


class DictParameter(Parameter):
    def __init__(self, dict_of_parameters):
        Parameter.__init__(self)
        self.dict_of_parameters = dict(dict_of_parameters)

    def draw(self, random):
        result = {}
        for k, v in self.dict_of_parameters.items():
            result[k] = v.draw(random)
        return result


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
            kwargs[name] = x
            children.append(name)

        for k, v in sorted(kwargs.items()):
            if hasattr(self, k):
                raise ValueError("Invalid parameter name %s" % (k,))
            if k not in children:
                children.append(k)
            setattr(self, k, v)
        self.children = tuple(children)
        if is_pure_tuple:
            self.Result = tuple
        else:
            self.Result = collections.namedtuple('Result', self.children)

    def draw(self, random):
        bits = [
            getattr(self, c).draw(random) for c in self.children
        ]
        if self.Result == tuple:
            return tuple(bits)
        else:
            return self.Result(*bits)
