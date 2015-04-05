from .strategies import SearchStrategy, check_data_type, check_length
from weakref import WeakKeyDictionary
from random import Random, getrandbits
from copy import deepcopy
from hypothesis.internal.compat import integer_types
import hashlib


class CollectionKey(object):
    def __init__(self):
        self.h = getrandbits(64)

    def __hash__(self):
        return self.h

    def __eq__(self, other):
        return self is other

    def __ne__(self, other):
        return self is not other


class BasicTemplate(object):
    def __init__(self, tracking_id):
        self.tracking_id = tracking_id
        self.collection_key = CollectionKey()

    def __trackas__(self):
        return (type(self).__name__, self.tracking_id)

    def __eq__(self, other):
        return (
            type(self) == type(other) and
            self.tracking_id == other.tracking_id
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.tracking_id)


def add_int_to_hasher(hasher, i):
    hasher.update(str(i).encode('utf-8'))


class Generated(BasicTemplate):

    def __init__(self, template_seed, parameter_seed):
        hasher = hashlib.sha1()
        add_int_to_hasher(hasher, template_seed)
        add_int_to_hasher(hasher, parameter_seed)
        super(Generated, self).__init__(hasher.digest())
        self.template_seed = template_seed
        self.parameter_seed = parameter_seed


class Simplified(BasicTemplate):

    def __init__(self, seed, iteration, source):
        hasher = hashlib.sha1()
        hasher.update(source.tracking_id)
        add_int_to_hasher(hasher, seed)
        add_int_to_hasher(hasher, iteration)
        super(Simplified, self).__init__(hasher.digest())
        self.seed = seed
        self.iteration = iteration
        self.source = source


class BasicSearchStrategy(SearchStrategy):

    def __init__(
        self,
        user_generate, user_parameter=None, user_simplify=None,
        copy_value=deepcopy,
    ):
        self.user_generate = user_generate
        self.user_parameter = user_parameter
        self.user_simplify = user_simplify or (lambda r, x: ())
        self.reify_cache = WeakKeyDictionary()
        self.copy_value = copy_value

    def produce_parameter(self, random):
        if self.user_parameter is not None:
            return random.getrandbits(64)
        else:
            return 0

    def produce_template(self, context, parameter):
        return Generated(
            context.random.getrandbits(64), parameter
        )

    def basic_simplify(self, random, template):
        random_seed = random.getrandbits(64)
        reified = self.reify(template)
        for i, simpler in enumerate(
            self.user_simplify(Random(random_seed), reified)
        ):
            new_template = Simplified(
                source=template, seed=random_seed, iteration=i
            )
            self.reify_cache[new_template.collection_key] = simpler
            yield new_template

    def reify(self, template):
        try:
            return self.reify_cache[template.collection_key]
        except KeyError:
            pass

        if isinstance(template, Generated):
            if self.user_parameter is None:
                parameter = None
            else:
                parameter = self.user_parameter(
                    Random(template.parameter_seed))
            result = self.user_generate(
                Random(template.template_seed), parameter)
        else:
            assert isinstance(template, Simplified)
            source = self.reify(template.source)
            for i, value in enumerate(
                self.user_simplify(Random(template.seed), source)
            ):
                if i == template.iteration:
                    result = value
                    break
            else:
                result = source
        self.reify_cache[template.collection_key] = result
        return self.copy_value(result)

    def to_basic(self, template):
        simplifications = []
        while isinstance(template, Simplified):
            simplifications.append([template.seed, template.iteration])
            template = template.source
        assert isinstance(template, Generated)
        return [
            template.template_seed, template.parameter_seed, simplifications]

    def from_basic(self, data):
        check_data_type(list, data)
        check_length(3, data)
        check_data_type(integer_types, data[0])
        check_data_type(integer_types, data[1])
        template = Generated(data[0], data[1])
        simplifications = data[2]
        while simplifications:
            step = simplifications.pop()
            check_data_type(list, step)
            check_length(2, step)
            seed, iteration = step
            template = Simplified(
                seed=seed, iteration=iteration, source=template)
        return template


def basic_strategy(
    generate,
    parameter=None, simplify=None, copy=deepcopy,
):
    return BasicSearchStrategy(
        user_generate=generate, user_parameter=parameter,
        user_simplify=simplify, copy_value=copy,
    )
