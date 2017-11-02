# frozen_string_literal: true

module Hypothesis
  module Providers
    def integers
      proc do |source|
        if source.bits(1).positive?
          source.bits(64)
        else
          0
        end
      end
    end

    def strings
      proc do |source|
        if source.bits(1).positive?
          'a'
        else
          'b'
        end
      end
    end
  end
end
