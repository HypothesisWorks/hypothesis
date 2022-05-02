#!/usr/bin/env bash


set -e -x

sudo ln -fs /usr/share/zoneinfo/UTC /etc/localtime

if [ ! $(which node) ] ; then
    # Ugh
    curl -sL https://deb.nodesource.com/setup_4.x | sudo -E bash -
fi

sudo apt-get install -y git libreadline-dev libssl-dev zlib1g-dev build-essential nodejs psmisc

if [ ! -d ~/.rbenv  ]; then
    git clone https://github.com/rbenv/rbenv.git ~/.rbenv
fi

if [ ! -d ~/.rbenv/plugins/ruby-build ]; then
    git clone https://github.com/rbenv/ruby-build.git ~/.rbenv/plugins/ruby-build
fi

cd /vagrant


export PATH="$HOME/.rbenv/bin:$PATH"

eval "$(rbenv init -)"

rbenv install -s 2.3.0

rbenv local 2.3.0

if [ ! $(which bundle) ] ; then
    gem install bundler
fi
bundle install

if [ ! $(killall bundle 2>/dev/null) ]; then
    sleep 1
    rm -f jekyll.log
fi

nohup bundle exec jekyll serve -H 0.0.0.0 --force_polling > jekyll.log 2>&1 &

sleep 1

cat jekyll.log
