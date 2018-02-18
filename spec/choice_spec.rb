# frozen_string_literal: true

RSpec.describe 'element_of possible' do
  include Hypothesis::Debug

  it 'includes the first argument' do
    find_any do
      m = any element_of([0, 1])
      m == 0
    end
  end

  it 'includes the last argument' do
    find_any do
      m = any element_of([0, 1, 2, 3])
      m == 3
    end
  end
end
