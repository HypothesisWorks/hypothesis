#!/bin/bash

set -e
set -x

if [[ "$(uname -s)" == 'Darwin' ]]; then
    DARWIN=true
else
    DARWIN=false
fi

if [[ "$DARWIN" = true ]]; then
    brew update

    if which pyenv > /dev/null; then
        eval "$(pyenv init -)"
    fi

    case "${TOXENV}" in
        py26)
            curl -O https://bootstrap.pypa.io/get-pip.py
            sudo python get-pip.py
            ;;
        py27)
            curl -O https://bootstrap.pypa.io/get-pip.py
            sudo python get-pip.py
            ;;
        py32)
            brew upgrade pyenv
            pyenv install 3.2.6
            pyenv global 3.2.6
            ;;
        py33)
            brew upgrade pyenv
            pyenv install 3.3.6
            pyenv global 3.3.6
            ;;
        py34)
            brew upgrade pyenv
            pyenv install 3.4.2
            pyenv global 3.4.2
            ;;
        pypy)
            brew upgrade pyenv
            pyenv install pypy-2.5.0
            pyenv global pypy-2.5.0
            ;;
        pypy3)
            brew upgrade pyenv
            pyenv install pypy3-2.4.0
            pyenv global pypy3-2.4.0
            ;;
        docs)
            curl -O https://bootstrap.pypa.io/get-pip.py
            sudo python get-pip.py
            ;;
    esac
    pyenv rehash

else
    sudo add-apt-repository -y ppa:fkrull/deadsnakes

    if [[ "${TOXENV}" == "pypy" ]]; then
        sudo add-apt-repository -y ppa:pypy/ppa
    fi

    if [[ "${OPENSSL}" == "0.9.8" ]]; then
        sudo add-apt-repository -y "deb http://archive.ubuntu.com/ubuntu/ lucid main"
    fi

    sudo apt-get -y update

    if [[ "${OPENSSL}" == "0.9.8" ]]; then
        sudo apt-get install -y --force-yes libssl-dev/lucid
    fi

    case "${TOXENV}" in
        py26)
            sudo apt-get install python2.6 python2.6-dev
            ;;
        py32)
            sudo apt-get install python3.2 python3.2-dev
            ;;
        py33)
            sudo apt-get install python3.3 python3.3-dev
            ;;
        py34)
            sudo apt-get install python3.4 python3.4-dev
            ;;
        py3pep8)
            sudo apt-get install python3.3 python3.3-dev
            ;;
        pypy)
            sudo apt-get install --force-yes pypy pypy-dev
            ;;
        docs)
            sudo apt-get install libenchant-dev
            ;;
    esac
fi

sudo -H pip install virtualenv
virtualenv ~/.venv
source ~/.venv/bin/activate
pip install --upgrade pip
pip install tox
