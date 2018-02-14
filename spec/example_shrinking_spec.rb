# frozen_string_literal: true

RSpec.describe 'shrinking' do
  include Hypothesis::Debug

  it 'finds lower bounds on integers' do
    n, = find { given(integers) >= 10 }
    expect(n).to eq(10)
  end

  it 'iterates to a fixed point' do
    @original = nil

    a, b = find do
      m = given integers
      n = given integers
      m > n && n > 0
    end

    expect(a).to eq(2)
    expect(b).to eq(1)
  end
end
