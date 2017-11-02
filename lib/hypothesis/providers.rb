module Hypothesis
  module Providers
    def integers
      return Proc.new do |source|
        if source.bits(1) > 0
          source.bits(64)
        else
          0
        end
      end
    end

    def strings
      return Proc.new do |source|
        if source.bits(1) > 0
          "a"
        else
          "b"
        end
      end
    end
  end
end
