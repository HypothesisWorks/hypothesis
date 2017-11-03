
# frozen_string_literal: true

module Hypothesis
  module World
    def self.current_engine
      if !defined? @current_engine
        nil
      else
        @current_engine
      end
    end

    def self.current_engine=(engine)
      @current_engine = engine
    end
  end
end
