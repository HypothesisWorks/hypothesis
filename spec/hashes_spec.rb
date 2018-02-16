# frozen_string_literal: true

RSpec.describe 'fixed hash providers' do
  they 'include all the keys' do
    hypothesis do
      x = given fixed_hashes(a: integers, b: integers)
      expect(x.size).to eq(2)
      expect(x[:a]).to be_a(Integer)
      expect(x[:b]).to be_a(Integer)
    end
  end
end

RSpec.describe 'variable hash providers' do
  they 'respect lower bounds' do
    hypothesis do
      x = given hashes(integers(min: 0, max: 4), strings, min_size: 4)
      expect(x.size).to be >= 4
    end
  end
end
