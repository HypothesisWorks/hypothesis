# frozen_string_literal: true

require 'minitest/autorun'
require 'hypothesis'

class TestMultipleFailures < Minitest::Test
  include Hypothesis
  include Hypothesis::Possibilities

  def test_multiple_failures
    assert_raises(Hypothesis::MultipleExceptionError) do
      @initial = nil

      hypothesis do
        x = any integers
        if @initial.nil?
          if x >= 1000
            @initial = x
          else
            next
          end
        end

        assert(x != @initial)
        raise 'Nope'
      end
    end
  end
end
