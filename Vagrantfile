# -*- mode: ruby -*-
# vi: set ft=ruby :

# This is a trivial Vagrantfile designed to simplify development of Hypothesis on Windows,
# where the normal make based build system doesn't work, or anywhere else where you would
# prefer a clean environment for Hypothesis development. It doesn't do anything more than spin
# up a suitable local VM for use with vagrant ssh. You should then use the Makefile from within
# that VM.

PROVISION = <<PROVISION

sudo apt-get install -y git libreadline-dev libssl-dev zlib1g-dev build-essential libbz2-dev libsqlite3-dev

if [ ! $(grep -q 'cd /vagrant' $HOME/.bashrc) ]; then
    echo 'cd /vagrant' >> $HOME/.bashrc
fi

cd /vagrant/

make install-tools

PROVISION

Vagrant.configure(2) do |config|

  config.vm.provider "virtualbox" do |v|
    v.memory = 1024
  end

  config.vm.box = "ubuntu/trusty64"

  config.vm.provision "shell", inline: PROVISION, privileged: false
end
