# frozen_string_literal: true

RSpec.describe 'choice_of provider' do
  include Hypothesis::Debug

  it 'includes the first argument' do
    find_any do
      m = given any_value_from([0, 1])
      m == 0
    end
  end

  it 'includes the last argument' do
    find_any do
      m = given any_value_from([0, 1, 2, 3])
      m == 3
    end
  end
end
