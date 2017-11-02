module Hypothesis
  class Engine
    attr_reader :current_source

    def initialize(options)
      @max_examples = options.fetch(:max_examples, 200)
      @random = Random.new(options.fetch(:seed, Random.new_seed))
    end

    def run(&test)
      @max_examples.times do
        @current_source = Source.new(@random)
        begin
          test.call(@current_source)
        rescue UnsatisfiedAssumption
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
        return 0
      else
        return @random.rand(2 ** n)
      end
    end

    def given(provider=nil, &block)
      provider ||= block
      return provider.call(self)
    end

    def assume(condition)
      if not condition
        raise UnsatisfiedAssumption.new()
      end
    end
  end
end
