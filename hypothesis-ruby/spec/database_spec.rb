# frozen_string_literal: true

RSpec.describe 'database usage' do
  it 'saves a minimal failing example' do
    expect do
      hypothesis do
        n = any integer
        expect(n).to be < 10
      end
    end.to raise_exception(RSpec::Expectations::ExpectationNotMetError)

    saved = Dir.glob("#{Hypothesis::DEFAULT_DATABASE_PATH}/*/*")
    expect(saved.length).to be == 1
  end

  it 'can be disabled' do
    expect do
      hypothesis(database: false) do
        n = any integer
        expect(n).to be < 10
      end
    end.to raise_exception(RSpec::Expectations::ExpectationNotMetError)
    expect(File.exist?(Hypothesis::DEFAULT_DATABASE_PATH)).to be false
  end

  it 'replays a previously failing example' do
    # This is a very unlikely value to be hit on by random. The first
    # time we run the test we fail for any value larger than it.
    # This then shrinks to exactly equal to magic. The second time we
    # run the test we only fail in this exact magic value. This
    # demonstrates replay from the previous test is working.
    magic = 17_658

    expect do
      hypothesis do
        n = any integer
        expect(n).to be < magic
      end
    end.to raise_exception(RSpec::Expectations::ExpectationNotMetError)

    expect do
      hypothesis do
        n = any integer
        expect(n).not_to be == magic
      end
    end.to raise_exception(RSpec::Expectations::ExpectationNotMetError)
  end

  it 'cleans out passing examples' do
    expect do
      hypothesis do
        n = any integer
        expect(n).to be < 10
      end
    end.to raise_exception(RSpec::Expectations::ExpectationNotMetError)

    saved = Dir.glob("#{Hypothesis::DEFAULT_DATABASE_PATH}/*/*")
    expect(saved.length).to be == 1

    hypothesis do
      any integer
    end

    saved = Dir.glob("#{Hypothesis::DEFAULT_DATABASE_PATH}/*/*")
    expect(saved.length).to be == 0
  end
end
