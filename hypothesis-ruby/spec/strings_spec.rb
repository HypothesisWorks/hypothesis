# frozen_string_literal: true

RSpec.describe 'strings' do
  they 'respect a non-ascii lower bound' do
    hypothesis do
      expect(any(codepoints(min: 127))).to be >= 127
    end
  end
end

RSpec.describe 'strings' do
  include Hypothesis::Debug

  they 'can be ascii' do
    find_any do
      s = any(strings(min_size: 3, max_size: 3))
      s.codepoints.all? { |c| c < 127 }
    end
  end

  they 'can be non-ascii' do
    find_any do
      any(strings).codepoints.any? { |c| c > 127 }
    end
  end

  they 'produce valid strings' do
    find do
      s = any(strings)
      # Shrinking will try and fail to move this into
      # an invalid codepoint range.
      !s.empty? && s.codepoints[0] >= 56_785
    end
  end
end
