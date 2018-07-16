# frozen_string_literal: true

RSpec.describe 'backtrace manipulation' do
  JD = Hypothesis::HypothesisJunkDrawer

  it 'identifies the test file as relevant' do
    JD.find_first_relevant_line(caller).include?('backtrace_spec.rb')
  end

  it 'prunes out hypothesis and rspec related lines' do
    hypothesis do
      relevant = JD.prune_backtrace(caller)
      relevant.each do |e|
        expect(e).to_not include(JD::HYPOTHESIS_ROOT)
        expect(e).to_not include('/rspec-core/')
      end
      expect(relevant.grep(/backtrace_spec.rb/)).to_not be_empty
    end
  end
end
