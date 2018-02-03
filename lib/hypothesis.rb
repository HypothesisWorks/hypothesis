# frozen_string_literal: true

require 'hypothesis/errors'
require 'hypothesis/providers'
require 'hypothesis/engine'
require 'hypothesis/world'
require 'hypothesis/debug'

module Hypothesis
  HYPOTHESIS_LOCATION = File.dirname(__FILE__)

  def hypothesis_stable_identifier
    # Attempt to get a "stable identifier" for any given
    # call into hypothesis. We use these to create
    # database keys (or will when we have a database) that
    # are stable across runs, so that when a test that
    # previously failed is rerun, we can fetch and reuse
    # the previous examples.

    # Note that essentially any answer to this method is
    # "fine" in that the failure mode is that sometiems we
    # just won't run the same test, but it's nice to keep
    # this as stable as possible if the code isn't changing.

    # Minitest makes it nice and easy to create a stable
    # test identifier, because it follows the classic xunit
    # pattern where a test is just a method invocation on a
    # fresh test class instance and it's easy to find out
    # which invocation that was.
    return "#{self.class.name}::#{@NAME}" if defined? @NAME

    # If we are running in an rspec example then, sadly,
    # rspec take the entirely unreasonable stance that
    # the correct way to pass data to a test is by passing
    # it as a function argument. Honestly, what is this,
    # Haskell? Ahem. Perfectly reasonable design decisions
    # on rspec's part, this creates some annoying difficulties
    # for us. We solve this through brute force and ignorance
    # by relying on the information we want being in the
    # inspect for the Example object, even if it's just there
    # as a string.
    begin
      is_rspec = is_a? RSpec::Core::ExampleGroup
    rescue NameError
      is_rspec = false
    end

    if is_rspec
      return [
        self.class.description,
        inspect.match(/"([^"]+)"/)[1]
      ].join(' ')
    end

    # Fallback time! We just walk the stack until we find the
    # entry point into code we control. This will typically be
    # where "hypothesis" was called.
    Thread.current.backtrace.each do |line|
      return line unless line.include?(Hypothesis::HYPOTHESIS_LOCATION)
    end
    # This should never happen unless something very strange is
    # going on.
    raise 'BUG: Somehow we have no caller!'
  end

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
