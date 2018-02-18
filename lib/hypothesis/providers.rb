# frozen_string_literal: true

# @!visibility private
class HypothesisCoreRepeatValues
  def should_continue(source)
    result = _should_continue(source.wrapped_data)
    raise Hypothesis::DataOverflow if result.nil?
    result
  end
end

module Hypothesis
  class <<self
    include Hypothesis
  end

  # A Provider describes a range of valid values that
  # can be provided by {Hypothesis#any}.
  # This class should not be subclassed directly, but
  # instead should always be constructed using methods
  # from {Hypothesis::Providers}.
  class Provider
    # @!visibility private
    include Hypothesis

    # A Provider that provides values by drawing them from
    # this provider and passing them to the block argument.
    #
    # e.g. `integers.map { |i| i * 2 }` is a provider of
    # even integers.
    #
    # @return [Provider]
    # @yield A value from the current provider
    def map
      Implementations::CompositeProvider.new do
        yield any(self)
      end
    end

    alias collect map

    # A Provider providing values drawn from this
    # provider such that the block returns a true value.
    #
    # e.g. `integers.map { |i| i % 2 == 0}` is a provider of
    # even integers (but will typically be less efficient
    # than the one suggested in {Provider#map}.
    #
    # @note Similar warnings to {Hypothesis#assume} apply
    #   here: If the condition is difficult to satisfy this
    #   may impact the performance and quality of your
    #   testing.
    #
    # @return [Provider]
    # @yield A value from the current provider
    def select
      Implementations::CompositeProvider.new do
        result = nil
        4.times do |i|
          assume(i < 3)
          result = any self
          break if yield(result)
        end
        result
      end
    end

    alias filter select

    # @!visibility private
    module Implementations
      # @!visibility private
      class CompositeProvider < Provider
        def initialize(block = nil, &implicit)
          @block = block || implicit
        end

        # @!visibility private
        def provide(_source)
          @block.call
        end
      end

      # @!visibility private
      class ProviderFromCore < Provider
        def initialize(core_provider)
          @core_provider = core_provider
        end

        # @!visibility private
        def provide(data)
          result = @core_provider.provide(data.wrapped_data)
          raise Hypothesis::DataOverflow if result.nil?
          result
        end
      end
    end
  end

  # A module of many common {Provider} implementations.
  # You should use methods from here to construct providers
  # for your testing rather than subclassing Provider yourself.
  #
  # You can use methods from this module by including
  # Hypothesis::Providers in your tests, or by calling them
  # on the module object directly.
  #
  # Most methods in this module that return a Provider have
  # two names: A singular and a plural name. These are
  # simply aliases and are identical in every way, but are
  # provided to improve readability. For example
  # `any an_integer` reads better than `given integers`
  # but `arrays(of: integers)` reads better than
  # `arrays(of: an_integer)`.
  module Providers
    include Hypothesis

    class <<self
      include Providers
    end

    # composite lets you chain multiple providers together,
    # by providing whatever value results from its block.
    #
    # For example the following provides a list plus some
    # element from that list:
    #
    # ```ruby
    #   composite do
    #     ls = any list(of: integers)
    #     # Or min_size: 1 above, but this shows use of
    #     # assume
    #     assume(ls.size > 0)
    #     i = any element_of(ls)
    #     [ls, i]
    # ```
    #
    # @return [Provider] A provider that provides the result
    #   of the passed block.
    def composite(&block)
      Hypothesis::Provider::Implementations::CompositeProvider.new(block)
    end

    # A provider of boolean values
    # @return [Provider]
    def booleans
      integers(min: 0, max: 1).map { |i| i == 1 }
    end

    alias boolean booleans

    # A provider of unicode codepoints.
    # @return [Provider]
    # @param min [Integer] The smallest codepoint to provide
    # @param max [Integer] The largest codepoint to provide
    def codepoints(min: 1, max: 1_114_111)
      base = integers(min: min, max: max)
      if min <= 126
        from(integers(min: min, max: [126, max].min), base)
      else
        base
      end
    end

    alias codepoint codepoints

    # A provider of strings
    # @return [Provider]
    # @param codepoints [Provider, nil] A provider for the
    #   codepoints that will be found in the string. If nil,
    #   will default to self.codepoints. Values from this provider
    #   will be further filtered to ensure the generated string is
    #   valid.
    # @param min_size [Integer] The smallest valid length for a
    #   provided string
    # @param max_size [Integer] The smallest valid length for a
    #   provided string
    def strings(codepoints: nil, min_size: 0, max_size: 10)
      codepoints = self.codepoints if codepoints.nil?
      codepoints = codepoints.select do |i|
        begin
          [i].pack('U*').codepoints
          true
        rescue ArgumentError
          false
        end
      end
      arrays(of: codepoints, min_size: min_size, max_size: max_size).map do |ls|
        ls.pack('U*')
      end
    end

    alias string strings

    # A provider of hashes of a fixed shape
    # This is used for hashes where you know exactly what the
    # keys are, and may want to use different providers for
    # their values. For example, fixed_hashes(a: integers, b: booleans)
    # will give you values like `{a: 11, b: false}`.
    # @return [Provider]
    # @param hash [Hash] A hash describing the values to provide.
    #  The keys will be present unmodified in the provided hashes,
    #  and the values should be providers that will be used to provide
    #  the corresponding values.
    def hashes_of_shape(hash)
      composite do
        result = {}
        hash.each { |k, v| result[k] = any(v) }
        result
      end
    end

    alias hash_of_shape hashes_of_shape

    # A provider of hashes of variable shape, where the keys and
    # values are each drawn from a specified provider. For example
    # hashes(strings, strings) might provide `{"a" => "b"}`.
    # @return provider
    # @param keys [Provider] the provider that will provide keys
    # @param values [Provider] the provider that will provide values
    def hashes_with(keys:, values:, min_size: 0, max_size: 10)
      composite do
        result = {}
        rep = HypothesisCoreRepeatValues.new(
          min_size, max_size, (min_size + max_size) * 0.5
        )
        source = World.current_engine.current_source
        while rep.should_continue(source)
          key = any keys
          if result.include?(key)
            rep.reject
          else
            result[key] = any values
          end
        end
        result
      end
    end

    alias hash_with hashes_with

    # A provider of arrays of a fixed shape
    # This is used for arrays where you know exactly what the
    # keys are, and may want to use different providers for
    # their values. For example, fixed_arrays(strings, integers)
    # will give you values like ["a", 1]
    # @return [Provider]
    # @param elements [Array<Provider>] A variable number of providers.
    #   The provided array will have this many values, with each value
    #   drawn from the corresponding argument. If elements contains an
    #   array it will be flattened first, so e.g. fixed_arrays(a, b)
    #   is equivalent to fixed_arrays([a, b])
    def arrays_of_shape(*elements)
      elements = elements.flatten
      composite do
        elements.map { |e| any e }.to_a
      end
    end

    alias array_of_shape arrays_of_shape

    # A provider of arrays of variable shape.
    # This is used for arrays where all of the elements come from
    # the same provider and the size may vary.
    # For example, arrays(booleans) might provide [false, true, false].
    # @return [Provider]
    # @param element [Provider] A provider that will be used for drawing
    #   elements of the array.
    # @param min_size [Integer] The smallest valid size of a provided array
    # @param max_size [Integer] The largest valid size of a provided array
    def arrays(of:, min_size: 0, max_size: 10)
      composite do
        result = []
        rep = HypothesisCoreRepeatValues.new(
          min_size, max_size, (min_size + max_size) * 0.5
        )
        source = World.current_engine.current_source
        result.push any(of) while rep.should_continue(source)
        result
      end
    end

    alias array arrays

    # A provider that combines several other providers, so that it may
    # provide any value that could come from one of them.
    # For example, from(strings, integers) could provide either of "a"
    # or 1.
    # @note This has a slightly non-standard aliasing. It reads more
    #   nicely if you write `any from(a, b, c)` but e.g.
    #   `lists(of: mix_of(a, b, c))`.
    #
    # @return [Provider]
    # @param components [Array<Provider>] Providers from which the
    #   returned provider may draw values. If components contains an
    #   array it will be flattened first, so e.g. from(a, b)
    #   is equivalent to from([a, b])
    def from(*components)
      components = components.flatten
      indexes = from_hypothesis_core(
        HypothesisCoreBoundedIntegers.new(components.size - 1)
      )
      composite do
        i = any indexes
        any components[i]
      end
    end

    alias mix_of from

    # A provider for any one of a fixed list of values.
    # @note these values are provided as is, so if the provided
    #   values are mutated in the test you should be careful to make
    #   sure each test run gets a fresh list (if you use this provider
    #   in line in the test you don't need to worry about this, this
    #   is only a problem if you define the provider outside of your
    #   hypothesis block).
    # @return [Provider]
    # @param values [Enumerable] A collection of values that may be
    #   provided.
    def element_of(values)
      values = values.to_a
      indexes = from_hypothesis_core(
        HypothesisCoreBoundedIntegers.new(values.size - 1)
      )
      composite do
        values.fetch(any(indexes))
      end
    end

    alias elements_of element_of

    # A provider for integers
    # @return [Provider]
    # @param min [Integer] The smallest value integer to provide.
    # @param max [Integer] The largest value integer to provide.
    def integers(min: nil, max: nil)
      base = from_hypothesis_core HypothesisCoreIntegers.new
      if min.nil? && max.nil?
        base
      elsif min.nil?
        composite { max - any(base).abs }
      elsif max.nil?
        composite { min + any(base).abs }
      else
        bounded = from_hypothesis_core(
          HypothesisCoreBoundedIntegers.new(max - min)
        )
        if min.zero?
          bounded
        else
          composite { min + any(bounded) }
        end
      end
    end

    alias integer integers

    private

    def from_hypothesis_core(core)
      Hypothesis::Provider::Implementations::ProviderFromCore.new(
        core
      )
    end
  end
end
