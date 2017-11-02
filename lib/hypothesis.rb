module Hypothesis
  class Error < Exception
  end

  class UnsatisfiedAssumption < Error
  end

  class UsageError < Error
  end

  def hypothesis(options={}, &block)
    if defined? @current_hypothesis_engine and not @current_hypothesis_engine.nil?
      raise UsageError.new("Cannot nest hypothesis calls")
    end
    begin
      @current_hypothesis_engine = Engine.new(options) 
      @current_hypothesis_engine.run(&block)
    ensure
      @current_hypothesis_engine = nil
    end
  end

  def given(provider=nil, &block)
    if not defined? @current_hypothesis_engine or @current_hypothesis_engine.nil?
      raise UsageError.new("Cannot call given outside of a hypothesis block")
    end
    @current_hypothesis_engine.current_source.given(provider, &block)
  end

  def assume(condition)
    if not defined? @current_hypothesis_engine or @current_hypothesis_engine.nil?
      raise UsageError.new("Cannot call assume outside of a hypothesis block")
    end
    @current_hypothesis_engine.current_source.assume(condition)
  end 

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

  module Providers
    def integers
      return Proc.new do |source|
        if source.bits(1) > 0
          source.bits(64)
        else
          0
        end
      end
    end

    def strings
      return Proc.new do |source|
        if source.bits(1) > 0
          "a"
        else
          "b"
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
