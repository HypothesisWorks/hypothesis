# frozen_string_literal: true

require 'hypothesis/errors'
require 'hypothesis/providers'
require 'hypothesis/engine'
require 'hypothesis/world'
require 'hypothesis/debug'

module Hypothesis
  def hypothesis(options = {}, &block)
    unless World.current_engine.nil?
      raise UsageError, 'Cannot nest hypothesis calls'
    end
    begin
      World.current_engine = Engine.new(**options)
      World.current_engine.run(&block)
    ensure
      World.current_engine = nil
    end
  end

  def given(provider = nil, &block)
    if World.current_engine.nil?
      raise UsageError, 'Cannot call given outside of a hypothesis block'
    end
    World.current_engine.current_source.given(provider, &block)
  end

  def assume(condition)
    if World.current_engine.nil?
      raise UsageError, 'Cannot call assume outside of a hypothesis block'
    end
    World.current_engine.current_source.assume(condition)
  end
end
