# frozen_string_literal: true

def expect_failure(&block)
  expect(&block).to raise_exception(RSpec::Expectations::ExpectationNotMetError)
end

RSpec.describe 'basic hypothesis tests' do
  they 'think integer addition is commutative' do
    hypothesis do
      x = any integers
      y = any integers
      expect(x + y).to eq(y + x)
    end
  end

  they 'are able to find zero values' do
    expect_failure do
      hypothesis do
        x = any integers
        expect(x).not_to eq(0)
      end
    end
  end

  they 'are able to filter out values' do
    hypothesis do
      x = any integers
      assume x != 0
      1 / x
    end
  end

  they 'find that string addition is not commutative' do
    expect_failure do
      hypothesis do
        x = any strings
        y = any strings
        expect(x + y).to be == y + x
      end
    end
  end

  they 'raise unsatisfiable when all assumptions fail' do
    expect do
      hypothesis do
        any integers
        assume false
      end
    end.to raise_exception(Hypothesis::Unsatisfiable)
  end
end
