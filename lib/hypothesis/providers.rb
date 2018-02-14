# frozen_string_literal: true

module Hypothesis
  module Providers
    def bits(n)
      from_hypothesis_core HypothesisCoreBitProvider.new(n)
    end

    def composite(&block)
      Hypothesis::Provider::Implementations::CompositeProvider.new(block)
    end

    def repeated(min_count: 0, max_count: 10, average_count: 5.0)
      local_provider_implementation do |source, block|
        rep = HypothesisCoreRepeatValues.new(
          min_count, max_count, average_count
        )
        block.call while rep.should_continue(source.wrapped_data)
      end
    end

    def lists(element, min_size: 0, max_size: 10, average_size: 10)
      composite do
        result = []
        given repeated(
          min_count: min_size, max_count: max_size, average_count: average_size
        ) do
          result.push given(element)
        end
        result
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
          composite { |_source| min + given(bounded) }
        end
      end
    end

    def strings
      composite do |source|
        if source.given(bits(1)).positive?
          'a'
        else
          'b'
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
    module Implementations
      class CompositeProvider < Provider
        def initialize(block)
          @block = block
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
