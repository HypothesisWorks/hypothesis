# frozen_string_literal: true

module Hypothesis
  module Providers
    def bits(n)
      from_hypothesis_core HypothesisCoreBitProvider.new(n)
    end

    def composite(&block)
      Hypothesis::Provider::Implementations::CompositeProvider.new(block)
    end

    def integers
      composite do |source|
        if source.given(bits(1)).positive?
          source.given(bits(64))
        else
          0
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
    end
  end
end
