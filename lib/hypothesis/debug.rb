# frozen_string_literal: true

require 'hypothesis/errors'

module Hypothesis
  module Debug
    class NoSuchExample < HypothesisError
    end

    def find(options = {}, &block)
      unless Hypothesis::World.current_engine.nil?
        raise UsageError, 'Cannot nest hypothesis calls'
      end
      begin
        Hypothesis::World.current_engine = Hypothesis::Engine.new(**options)
        Hypothesis::World.current_engine.is_find = true
        Hypothesis::World.current_engine.run(&block)
        source = Hypothesis::World.current_engine.current_source
        raise NoSuchExample if source.nil?
        source.draws
      ensure
        Hypothesis::World.current_engine = nil
      end
    end

    def find_any(options = {}, &block)
      # Currently the same as find, but once we have config
      # options for shrinking it will turn that off.
      find(options, &block)
    end
  end
end
