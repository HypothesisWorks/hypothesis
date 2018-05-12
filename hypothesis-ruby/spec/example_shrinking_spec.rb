# frozen_string_literal: true

require 'set'

RSpec.describe 'shrinking' do
  include Hypothesis::Debug

  it 'finds lower bounds on integers' do
    n, = find { any(integers) >= 10 }
    expect(n).to eq(10)
  end

  it 'iterates to a fixed point' do
    @original = nil

    a, b = find do
      m = any integers
      n = any integers
      m > n && n > 0
    end

    expect(a).to eq(2)
    expect(b).to eq(1)
  end

  it 'can shrink through a chain' do
    ls, = find do
      x = any built_as do
        n = any integers(min: 1, max: 100)
        any arrays(of: integers(min: 0, max: 10), min_size: n, max_size: n)
      end
      x.sum >= 50
    end

    expect(ls).to_not include(0)
  end

  it 'can shrink through a chain without deleting first element' do
    10.times do
      ls, = find do
        x = any built_as do
          n = any integers(min: 1, max: 100)
          any arrays(of: integers(min: 0, max: 10), min_size: n, max_size: n)
        end
        assume x[0] > 0
        x.sum >= 50
      end

      expect(ls).to_not include(0)
    end
  end

  it 'can shrink duplicate elements' do
    10.times do
      ls, = find do
        x = any array(of: integers(min: 0, max: 100))
        significant = x.select { |n| n > 0 }
        Set.new(significant).length < significant.length
      end
      expect(ls).to eq([1, 1])
    end
  end
end
