# frozen_string_literal: true

RSpec.describe 'fixed arrays' do
  they 'are of fixed size and shape' do
    hypothesis do
      ls = given fixed_arrays(integers, strings, integers)
      expect(ls.size).to eq(3)
      expect(ls[0]).to be_a(Integer)
      expect(ls[2]).to be_a(Integer)
      expect(ls[1]).to be_a(String)
    end
  end
end
