# frozen_string_literal: true

RSpec.describe 'shrinking' do
  include Hypothesis::Debug

  it 'finds lower bounds on integers' do
    n, = find { given(integers) >= 10 }
    expect(n).to eq(10)
  end
end
