require "hypothesis/errors"
require "hypothesis/providers"
require "hypothesis/engine"

module Hypothesis
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
end
