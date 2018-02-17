# frozen_string_literal: true

RSpec.describe 'booleans' do
  include Hypothesis::Debug

  they 'can be true' do
    find_any { any booleans }
  end

  they 'can be false' do
    find_any { !any(booleans) }
  end
end
