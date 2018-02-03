# frozen_string_literal: true

require 'minitest/autorun'
require 'hypothesis'

class TestIdentifiers < Minitest::Test
  include Hypothesis

  def test_abc
    assert_equal hypothesis_stable_identifier, 'TestIdentifiers::test_abc'
  end
end
