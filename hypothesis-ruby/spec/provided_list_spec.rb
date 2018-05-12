# frozen_string_literal: true

RSpec.describe 'shrinking' do
  include Hypothesis::Debug
  include Hypothesis::Possibilities

  it 'finds a small list' do
    ls, = find { any(arrays(of: integers)).length >= 2 }
    expect(ls).to eq([0, 0])
  end

  it 'shrinks a list to its last element' do
    10.times do
      @original_target = nil

      ls, = find do
        v = any(arrays(of: integers))

        if v.length >= 5 && @original_target.nil? && v[-1] > 0
          @original_target = v
        end
        !@original_target.nil? && v && v[-1] == @original_target[-1]
      end

      expect(ls.length).to eq(1)
    end
  end
end
