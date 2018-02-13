# frozen_string_literal: true

RSpec.describe 'printing examples' do
  it 'adds a statement to the exceptions string' do
    expect do
      hypothesis do
        n = given integers
        expect(n).to eq(0)
      end
    end.to raise_exception(/Given #1/)
  end

  it 'adds multiple statements to the exceptions string' do
    expect do
      hypothesis do
        n = given integers
        m = given integers
        expect(n).to eq(m)
      end
    end.to raise_exception(/Given #1.+Given #2/m)
  end

  it 'includes the name in the Given' do
    expect do
      hypothesis do
        n = given integers, name: 'fred'
        expect(n).to eq(1)
      end
    end.to raise_exception(/Given fred:/)
  end

  it 'does not mangle names if you reuse exceptions' do
    shared = Exception.new('Stuff')
    3.times do
      expect do
        hypothesis do
          given integers
          raise shared
        end
      end.to raise_exception do |ex|
        expect(ex).to equal(shared)
        expect(ex.to_s.scan(/Given/).count).to eq(1)
        expect(ex.to_s.scan(/Stuff/).count).to eq(1)
      end
    end
  end

  it 'does not include nested givens in printing' do
    expect do
      hypothesis do
        value = given(composite do |source|
          source.given integers
          source.given integers
          source.given integers
        end)
        expect(value).to eq(0)
      end
    end.to raise_exception(RSpec::Expectations::ExpectationNotMetError) do |ex|
      expect(ex.to_s.scan(/Given/).count).to eq(1)
    end
  end

  it 'includes Given in inspect as well as to_s' do
    expect do
      hypothesis do
        n = given integers
        expect(n).to eq(0)
      end
    end.to raise_exception do |ex|
      expect(ex.inspect).to match(/Given #1/)
    end
  end
end
