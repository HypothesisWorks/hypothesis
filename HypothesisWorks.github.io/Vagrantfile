# -*- mode: ruby -*-
# vi: set ft=ruby :



Vagrant.configure(2) do |config|
  config.vm.provider "vmware_workstation" do |v|
    v.memory = 1024
  end

  config.vm.box = "hashicorp/precise64"
  config.vm.network "forwarded_port", guest: 4000, host: 4000
  config.vm.provision "shell", path: "provision.sh", privileged: false
end
