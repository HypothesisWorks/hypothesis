# frozen_string_literal: true

module Hypothesis
  module Debug
    def find(options = {}, &block)
      unless Hypothesis::World.current_engine.nil?
        raise UsageError, 'Cannot nest hypothesis calls'
      end
      begin
        Hypothesis::World.current_engine = Hypothesis::Engine.new(**options)
        Hypothesis::World.current_engine.is_find = true
        Hypothesis::World.current_engine.run(&block)
        Hypothesis::World.current_engine.current_source.draws
      ensure
        Hypothesis::World.current_engine = nil
      end
    end
  end
end
