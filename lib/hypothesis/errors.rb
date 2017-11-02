# frozen_string_literal: true

module Hypothesis
  class Error < RuntimeError
  end

  class UnsatisfiedAssumption < Error
  end

  class UsageError < Error
  end
end
