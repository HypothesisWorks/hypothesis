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

  # A Possible describes a range of valid values that
  # can result from a call to {Hypothesis#any}.
  # This class should not be subclassed directly, but
  # instead should always be constructed using methods
  # from {Hypothesis::Possibilities}.
  class Possible
    # @!visibility private
    include Hypothesis

    # A Possible value constructed by passing one of these
    # Possible values to the provided block.
    #
    # e.g. the Possible values of `integers.map { |i| i * 2 }`
    # are all even integers.
    #
    # @return [Possible]
    # @yield A possible value of self.
    def map
      Implementations::CompositePossible.new do
        yield any(self)
      end
    end

    alias collect map

    # One of these Possible values selected such that
    # the block returns a true value for it.
    #
    # e.g. the Possible values of
    # `integers.filter { |i| i % 2 == 0}`  are all even
    # integers (but will typically be less efficient
    # than the one suggested in {Possible#map}.
    #
    # @note Similar warnings to {Hypothesis#assume} apply
    #   here: If the condition is difficult to satisfy this
    #   may impact the performance and quality of your
    #   testing.
    #
    # @return [Possible]
    # @yield A possible value of self.
    def select
      Implementations::CompositePossible.new do
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
      class CompositePossible < Possible
        def initialize(block = nil, &implicit)
          @block = block || implicit
        end

        # @!visibility private
        def provide(&block)
          (@block || block).call
        end
      end

      # @!visibility private
      class PossibleFromCore < Possible
        def initialize(core_possible)
          @core_possible = core_possible
        end

        # @!visibility private
        def provide
          data = World.current_engine.current_source
          result = @core_possible.provide(data.wrapped_data)
          raise Hypothesis::DataOverflow if result.nil?
          result
        end
      end
    end
  end

  # A module of many common {Possible} implementations.
  # Rather than subclassing Possible yourself you should use
  # methods from this module to construct Possible values.`
  #
  # You can use methods from this module by including
  # Hypothesis::Possibilities in your tests, or by calling them
  # on the module object directly.
  #
  # Most methods in this module that return a Possible have
  # two names: A singular and a plural name. These are
  # simply aliases and are identical in every way, but are
  # provided to improve readability. For example
  # `any integer` reads better than `any integers`
  # but `arrays(of: integers)` reads better than
  # `arrays(of: integer)`.
  module Possibilities
    include Hypothesis

    class <<self
      include Possibilities
    end

    # built_as lets you chain multiple Possible values together,
    # by providing whatever value results from its block.
    #
    # For example the following provides an array plus some
    # element from that array:
    #
    # ```ruby
    #   built_as do
    #     ls = any array(of: integers)
    #     # Or min_size: 1 above, but this shows use of
    #     # assume
    #     assume ls.size > 0
    #     i = any element_of(ls)
    #     [ls, i]
    #   end
    # ```
    #
    # @return [Possible] A Possible whose possible values are
    #   any result from the passed block.
    def built_as(&block)
      Hypothesis::Possible::Implementations::CompositePossible.new(block)
    end

    alias values_built_as built_as

    # A Possible boolean value
    # @return [Possible]
    def booleans
      integers(min: 0, max: 1).map { |i| i == 1 }
    end

    alias boolean booleans

    # A Possible unicode codepoint.
    # @return [Possible]
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

    # A Possible String
    # @return [Possible]
    # @param codepoints [Possible, nil] The Possible codepoints
    #   that can be found in the string. If nil,
    #   will default to self.codepoints. These
    #   will be further filtered to ensure the generated string is
    #   valid.
    # @param min_size [Integer] The smallest valid length for a
    #   provided string
    # @param max_size [Integer] The largest valid length for a
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

    # A Possible Hash, where all possible values have a fixed
    # shape.
    # This is used for hashes where you know exactly what the
    # keys are, and different keys may have different possible values.
    # For example, hashes_of_shape(a: integers, b: booleans)
    # will give you values like `{a: 11, b: false}`.
    # @return [Possible]
    # @param hash [Hash] A hash describing the values to provide.
    #  The keys will be present unmodified in the provided hashes,
    #  mapping to their Possible value in the result.
    def hashes_of_shape(hash)
      built_as do
        result = {}
        hash.each { |k, v| result[k] = any(v) }
        result
      end
    end

    alias hash_of_shape hashes_of_shape

    # A Possible Hash of variable shape.
    # @return [Possible]
    # @param keys [Possible] the possible keys
    # @param values [Possible] the possible values
    def hashes_with(keys:, values:, min_size: 0, max_size: 10)
      built_as do
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

    # A Possible Arrays of a fixed shape.
    # This is used for arrays where you know exactly how many
    # elements there are, and different values may be possible
    # at different positions.
    # For example, arrays_of_shape(strings, integers)
    # will give you values like ["a", 1]
    # @return [Possible]
    # @param elements [Array<Possible>] A variable number of Possible.
    #   values. The provided array will have this many values, with
    #   each value possible for the corresponding argument. If elements
    #   contains an array it will be flattened first, so e.g.
    #   arrays_of_shape(a, b) is equivalent to arrays_of_shape([a, b])
    def arrays_of_shape(*elements)
      elements = elements.flatten
      built_as do
        elements.map { |e| any e }.to_a
      end
    end

    alias array_of_shape arrays_of_shape

    # A Possible Array of variable shape.
    # This is used for arrays where the size may vary and the same values
    # are possible at any position.
    # For example, arrays(of: booleans) might provide [false, true, false].
    # @return [Possible]
    # @param of [Possible] The possible elements of the array.
    # @param min_size [Integer] The smallest valid size of a provided array
    # @param max_size [Integer] The largest valid size of a provided array
    def arrays(of:, min_size: 0, max_size: 10)
      built_as do
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

    # A Possible where the possible values are any one of a number
    # of other possible values.
    # For example, from(strings, integers) could provide either of "a"
    # or 1.
    # @note This has a slightly non-standard aliasing. It reads more
    #   nicely if you write `any from(a, b, c)` but e.g.
    #   `arrays(of: mix_of(a, b, c))`.
    #
    # @return [Possible]
    # @param components [Array<Possible>] A number of Possible values,
    #   where the result will include any value possible from any of
    #   them. If components contains an
    #   array it will be flattened first, so e.g. from(a, b)
    #   is equivalent to from([a, b])
    def from(*components)
      components = components.flatten
      indexes = from_hypothesis_core(
        HypothesisCoreBoundedIntegers.new(components.size - 1)
      )
      built_as do
        i = any indexes
        any components[i]
      end
    end

    alias mix_of from

    # A Possible where any one of a fixed array of values is possible.
    # @note these values are provided as is, so if the provided
    #   values are mutated in the test you should be careful to make
    #   sure each test run gets a fresh value (if you use this Possible
    #   in line in the test you don't need to worry about this, this
    #   is only a problem if you define the Possible outside of your
    #   hypothesis block).
    # @return [Possible]
    # @param values [Enumerable] A collection of possible values.
    def element_of(values)
      values = values.to_a
      indexes = from_hypothesis_core(
        HypothesisCoreBoundedIntegers.new(values.size - 1)
      )
      built_as do
        values.fetch(any(indexes))
      end
    end

    alias elements_of element_of

    # A Possible integer
    # @return [Possible]
    # @param min [Integer] The smallest value integer to provide.
    # @param max [Integer] The largest value integer to provide.
    def integers(min: nil, max: nil)
      base = from_hypothesis_core HypothesisCoreIntegers.new
      if min.nil? && max.nil?
        base
      elsif min.nil?
        built_as { max - any(base).abs }
      elsif max.nil?
        built_as { min + any(base).abs }
      else
        bounded = from_hypothesis_core(
          HypothesisCoreBoundedIntegers.new(max - min)
        )
        if min.zero?
          bounded
        else
          built_as { min + any(bounded) }
        end
      end
    end

    alias integer integers

    private

    def from_hypothesis_core(core)
      Hypothesis::Possible::Implementations::PossibleFromCore.new(
        core
      )
    end
  end
end
