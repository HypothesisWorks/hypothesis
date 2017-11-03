# frozen_string_literal: true

require "helix_runtime"
require "hypothesis/native"

module Hypothesis
  class Engine
    attr_reader :current_source

    def initialize(options)
      @max_examples = options.fetch(:max_examples, 200)
      @random = Random.new(options.fetch(:seed, Random.new_seed))
    end

    def run
      count = 0
      while count < @max_examples
        @current_source = Source.new(@random)
        count += 1
        begin
          yield(@current_source)
        rescue UnsatisfiedAssumption
          count -= 1
        end
      end
    end
  end

  class Source
    attr_reader :random

    def initialize(random)
      @random = random
    end

    def bits(n)
      if n <= 0
        0
      else
        @random.rand(2**n)
      end
    end

    def given(provider = nil, &block)
      provider ||= block
      provider.call(self)
    end

    def assume(condition)
      raise UnsatisfiedAssumption unless condition
    end
  end
end
