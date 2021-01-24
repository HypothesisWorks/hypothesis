RSpec.describe 'specifying which phases to include' do
  include Hypothesis::Debug

  it 'alerts of improper phase names' do
    expect do
      hypothesis(phases: [:sHrInK]) { any(integers) }
    end.to raise_exception(ArgumentError, 'Cannot convert to Phase: sHrInK is not a valid Phase')
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
