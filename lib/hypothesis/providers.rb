# frozen_string_literal: true

module Hypothesis
  module Providers
    def bits(n)
      from_hypothesis_core HypothesisCoreBitProvider.new(n)
    end

    def composite(&block)
      Hypothesis::Provider::Implementations::CompositeProvider.new(self, block)
    end

    def integers
      composite do
        if given(bits(1)).positive?
          given(bits(64))
        else
          0
        end
      end
    end

    def strings
      composite do
        if given(bits(1)).positive?
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
      class CompositeObject
        def initialize(parent, source)
          @parent = parent
          @source = source
        end

        def given(provider)
          @source.given(provider)
        end

        def assume(condition)
          @source.assume(condition)
        end

        def respond_to_missing?(name)
          @parent.respond_to? name
        end

        def method_missing(name, *args, &block)
          @parent.send(name, *args, &block)
        end
      end

      class CompositeProvider < Provider
        def initialize(parent, block)
          @parent = parent
          @block = block
        end

        def provide(source)
          CompositeObject.new(@parent, source).instance_eval(&@block)
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
