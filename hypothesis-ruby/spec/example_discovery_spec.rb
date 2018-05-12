# frozen_string_literal: true

RSpec.describe 'hypothesis' do
  include Hypothesis::Debug

  it 'can find mid sized integers' do
    n, = find do
      m = any(integers)
      m >= 100 && m <= 1000
    end
    expect(n).to eq(100)
  end
end
