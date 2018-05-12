#!/usr/bin/env bash

set -e -o xtrace

rm -rf isolated
mkdir isolated

bundle exec rake gem

mv hypothesis-specs*.gem isolated
cp -Rl .rspec spec isolated

cd isolated

mkdir gems
export GEM_HOME="$PWD"/gems
export GEM_PATH="$GEM_HOME"

gem install ./hypothesis-specs*.gem
gem install rspec simplecov

gems/bin/rspec spec
