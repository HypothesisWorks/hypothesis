# frozen_string_literal: true

RSpec.describe 'fixed hash possibles' do
  they 'include all the keys' do
    hypothesis do
      x = any hash_of_shape(a: integers, b: integers)
      expect(x.size).to eq(2)
      expect(x[:a]).to be_a(Integer)
      expect(x[:b]).to be_a(Integer)
    end
  end
end

RSpec.describe 'variable hash possibles' do
  they 'respect lower bounds' do
    hypothesis do
      x = any hash_with(
        keys: integers(min: 0, max: 4),
        values: strings,
        min_size: 4
      )
      expect(x.size).to be >= 4
    end
  end
end
