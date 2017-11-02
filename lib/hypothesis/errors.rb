module Hypothesis
  class Error < Exception
  end

  class UnsatisfiedAssumption < Error
  end

  class UsageError < Error
  end
end
