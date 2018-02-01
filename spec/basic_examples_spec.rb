# frozen_string_literal: true

def expect_failure(&block)
  expect(&block).to raise_exception(RSpec::Expectations::ExpectationNotMetError)
end

RSpec.describe 'basic hypothesis tests' do
  it 'think integer addition is commutative' do
    hypothesis do
      x = given integers
      y = given integers
      expect(x + y).to eq(y + x)
    end
  end

  it 'are able to find zero values' do
    expect_failure do
      hypothesis do
        x = given integers
        expect(x).not_to eq(0)
      end
    end
  end

  it 'are able to filter out values' do
    hypothesis do
      x = given integers
      assume x != 0
      1 / x
    end
  end

  it 'find that string addition is not commutative' do
    expect_failure do
      hypothesis do
        x = given strings
        y = given strings
        expect(x + y).to be == y + x
      end
    end
  end
end
