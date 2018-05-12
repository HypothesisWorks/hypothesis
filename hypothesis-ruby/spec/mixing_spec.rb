# frozen_string_literal: true

RSpec.describe 'from possible' do
  include Hypothesis::Debug

  it 'includes the first argument' do
    find_any do
      any(from(integers, strings)).is_a? Integer
    end
  end

  it 'includes the second argument' do
    find_any do
      any(from(integers, strings)).is_a? String
    end
  end
end
