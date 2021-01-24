# frozen_string_literal: true

RSpec.describe 'specifying which phases to include' do
  include Hypothesis::Debug

  it 'alerts of improper phase names' do
    expect do
      hypothesis(phases: [:sHrInK])
    end.to raise_exception(
      ArgumentError,
      'Cannot convert to Phase: sHrInK is not a valid Phase'
    )
  end

  it 'alerts of attempting to exclude an unknown phase' do
    expect do
      hypothesis(phases: Phase.excluding(:unknown))
    end.to raise_exception(
      ArgumentError,
      'Attempting to exclude unknown phases: [:unknown]'
    )
  end

  it 'does not shrink when shrinking is skipped' do
    n = 0
    10.times do
      n, = find(phases: Phase.excluding(:shrink)) { any(integers) >= 10 }
      break if n != 10
    end

    expect(n).to_not eq(10)
  end
end
