# frozen_string_literal: true

class HypothesisCoreRepeatValues
  def should_continue(source)
    result = _should_continue(source.wrapped_data)
    raise Hypothesis::DataOverflow if result.nil?
    result
  end
end

module Hypothesis
  module Providers
    def composite(&block)
      Hypothesis::Provider::Implementations::CompositeProvider.new(block)
    end

    def codepoints(min: 1, max: 1_114_111)
      base = integers(min: min, max: max)
      if min <= 126
        mixed(integers(min: min, max: [126, max].min), base)
      else
        base
      end
    end

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
      arrays(codepoints, min_size: min_size, max_size: max_size).map do |ls|
        ls.pack('U*')
      end
    end

    def arrays(element, min_size: 0, max_size: 10)
      composite do |source|
        result = []
        rep = HypothesisCoreRepeatValues.new(
          min_size, max_size, (min_size + max_size) * 0.5
        )
        result.push source.given(element) while rep.should_continue(source)
        result
      end
    end

    def mixed(*args)
      args = args.flatten
      indexes = from_hypothesis_core(
        HypothesisCoreBoundedIntegers.new(args.size - 1)
      )
      composite do |source|
        i = source.given(indexes)
        source.given(args[i])
      end
    end

    def choice_of(values)
      indexes = from_hypothesis_core(
        HypothesisCoreBoundedIntegers.new(values.size - 1)
      )
      composite do |source|
        values.fetch(source.given(indexes))
      end
    end

    def integers(min: nil, max: nil)
      base = from_hypothesis_core HypothesisCoreIntegers.new
      if min.nil? && max.nil?
        base
      elsif min.nil?
        composite { |source| max - source.given(base).abs }
      elsif max.nil?
        composite { |source| min + source.given(base).abs }
      else
        bounded = from_hypothesis_core(
          HypothesisCoreBoundedIntegers.new(max - min)
        )
        if min.zero?
          bounded
        else
          composite { |source| min + source.given(bounded) }
        end
      end
    end

    private

    def from_hypothesis_core(core)
      Hypothesis::Provider::Implementations::ProviderFromCore.new(
        core
      )
    end

    def local_provider_implementation(&block)
      Hypothesis::Provider::Implementations::ProviderFromBlock.new(
        block
      )
    end
  end

  class Provider
    def map
      Implementations::CompositeProvider.new do |source|
        yield(source.given(self))
      end
    end

    def select
      Implementations::CompositeProvider.new do |source|
        result = nil
        4.times do |i|
          source.assume(i < 3)
          result = source.given(self)
          break if yield(result)
        end
        result
      end
    end

    module Implementations
      class CompositeProvider < Provider
        def initialize(block = nil, &implicit)
          @block = block || implicit
        end

        def provide(source)
          @block.call(source)
        end
      end

      class ProviderFromCore < Provider
        def initialize(core_provider)
          @core_provider = core_provider
        end

        def provide(data)
          result = @core_provider.provide(data.wrapped_data)
          raise Hypothesis::DataOverflow if result.nil?
          result
        end
      end

      class ProviderFromBlock < Provider
        def initialize(block)
          @block = block
        end

        def provide(data, &block)
          @block.call(data, block)
        end
      end
    end
  end
end
