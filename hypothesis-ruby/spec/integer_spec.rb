# frozen_string_literal: true

RSpec.describe 'integer possibles' do
  they 'respect upper bounds' do
    hypothesis do
      expect(any(integers(max: 100))).to be <= 100
    end
  end

  they 'respect lower bounds' do
    hypothesis do
      expect(any(integers(min: -100))).to be >= -100
    end
  end

  they 'respect both bounds at once when lower bound is zero' do
    hypothesis do
      n = any integers(min: 0, max: 100)
      expect(n).to be <= 100
      expect(n).to be >= 0
    end
  end

  they 'respect both bounds at once when lower bound is non-zero' do
    hypothesis do
      n = any integers(min: 1, max: 100)
      expect(n).to be <= 100
      expect(n).to be >= 1
    end
  end
end
