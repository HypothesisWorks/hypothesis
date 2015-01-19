from hypothesis.internal.compat import binary_type, text_type, hrange
from hypothesis.descriptors import (
    just, Just,
    OneOf, sampled_from, SampledFrom
)
from hypothesis.searchstrategy import (
    SearchStrategy, RandomWithSeed, nice_string
)
import hypothesis.params as params
from hypothesis.internal.utils.distributions import geometric, biased_coin
from random import Random
from collections import namedtuple
from tests.common import small_table
from hypothesis.database.converter import ConverterTable

primitive_types = [int, float, text_type, binary_type, bool, complex]
basic_types = list(primitive_types)
basic_types.append(OneOf(tuple(basic_types)))
basic_types += [frozenset({x}) for x in basic_types]
basic_types += [set({x}) for x in basic_types]
basic_types.append(Random)
branch_types = [dict, tuple, list]

Descriptor = namedtuple('Descriptor', ('descriptor',))


class DescriptorWithValue(namedtuple(
        'DescriptorWithValue', ('descriptor', 'value', 'parameter', 'random'))
):
    def __repr__(self):
        return "DescriptorWithValue(descriptor=%s, value=%r)" % (
            nice_string(self.descriptor), self.value
        )

ConverterTable.default().mark_not_serializeable(Descriptor)
ConverterTable.default().mark_not_serializeable(DescriptorWithValue)


class DescriptorStrategy(SearchStrategy):
    descriptor = Descriptor

    def __init__(self):
        self.key_strategy = small_table.strategy(
            OneOf((text_type, binary_type, int, bool))
        )
        self.sampling_strategy = small_table.strategy(primitive_types)
        self.parameter = params.CompositeParameter(
            leaf_descriptors=params.NonEmptySubset(basic_types),
            branch_descriptors=params.NonEmptySubset(branch_types),
            branch_factor=params.UniformFloatParameter(0.6, 0.99),
            key_parameter=self.key_strategy.parameter,
            just_probability=params.UniformFloatParameter(0, 0.45),
            sampling_probability=params.UniformFloatParameter(0, 0.45),
            sampling_param=self.sampling_strategy.parameter,
        )

    def produce(self, random, pv):
        n_children = geometric(random, pv.branch_factor)
        if not n_children:
            return random.choice(pv.leaf_descriptors)
        elif n_children == 1 and biased_coin(random, pv.just_probability):
            new_desc = self.produce(random, pv)
            child_strategy = small_table.strategy(new_desc)
            pv2 = child_strategy.parameter.draw(random)
            return just(child_strategy.produce(random, pv2))
        elif n_children == 1 and biased_coin(random, pv.sampling_probability):
            elements = self.sampling_strategy.produce(
                random, pv.sampling_param)
            if elements:
                return sampled_from(elements)

        children = [self.produce(random, pv) for _ in hrange(n_children)]
        combiner = random.choice(pv.branch_descriptors)
        if combiner != dict:
            return combiner(children)
        else:
            result = {}
            for v in children:
                k = self.key_strategy.produce(random, pv.key_parameter)
                result[k] = v
            return result

    def simplify(self, value):
        if isinstance(value, dict):
            children = list(value.values())
        elif isinstance(value, (Just, SampledFrom)):
            return
        elif isinstance(value, (list, set, tuple)):
            children = list(value)
        else:
            return
        for child in children:
            yield child

    def could_have_produced(self, value):
        return True


small_table.define_specification_for(
    Descriptor, lambda s, d: DescriptorStrategy())


class DescriptorWithValueStrategy(SearchStrategy):
    descriptor = DescriptorWithValue

    def __init__(self, strategy_table):
        descriptor_strategy = strategy_table.strategy(Descriptor)
        self.descriptor_strategy = descriptor_strategy
        self.parameter = descriptor_strategy.parameter
        self.strategy_table = strategy_table
        self.random_strategy = strategy_table.strategy(Random)

    def produce(self, random, pv):
        descriptor = self.descriptor_strategy.produce(random, pv)
        strategy = self.strategy_table.strategy(descriptor)
        parameter = strategy.parameter.draw(random)
        value = strategy.produce(random, parameter)
        new_random = self.random_strategy.draw_and_produce(random)
        return DescriptorWithValue(
            descriptor=descriptor,
            parameter=parameter,
            value=value,
            random=new_random,
        )

    def simplify(self, dav):
        random = RandomWithSeed(dav.random.seed)
        for d in self.descriptor_strategy.simplify(dav.descriptor):
            strat = self.strategy_table.strategy(d)
            param = strat.parameter.draw(random)
            value = strat.produce(random, param)
            yield DescriptorWithValue(
                descriptor=d,
                parameter=param,
                value=value,
                random=RandomWithSeed(dav.random.seed)
            )
        for v in (
            self.strategy_table.strategy(
                dav.descriptor).simplify(dav.value)
        ):
            yield DescriptorWithValue(
                descriptor=dav.descriptor,
                parameter=dav.parameter,
                value=v,
                random=RandomWithSeed(dav.random.seed)
            )


small_table.define_specification_for(
    DescriptorWithValue,
    lambda s, d: DescriptorWithValueStrategy(s),
)
