#!/bin/bash

continuing=true
if ! command -v python3 &> /dev/null
then
    while true; do
        read -p "Python3 not detected. Would you like to automatically install python 3.6 now with sudo apt-get? (y/n):" yn
        case $yn in
            [Yy]* ) sudo apt update -y && sudo apt-get install python3.6 -y; break;;
            [Nn]* ) continuing=false; break;;
            * ) echo "Please answer yes (y/Y) or no (n/N).";;
        esac
    done
endif

if [ "$continuing" = true ]; then

if ! command -v pip &> /dev/null
then
    while true; do
        read -p "pip not detected. Would you like to automatically install python3-pip now with sudo apt-get? (y/n):" yn
        case $yn in
            [Yy]* ) sudo apt update -y && sudo apt-get install python3-pip -y; break;;
            [Nn]* ) continuing=false; break;;
            * ) echo "Please answer yes (y/Y) or no (n/N).";;
        esac
    done
fi

if [ "$continuing" = true ]; then

pip install openai

if ! command -v yarn &> /dev/null 
then
    echo "yarn not detected. Installing..."
    if ! command -v npm &> /dev/null
    then
        echo "nvm not detected, installing it:"
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash
    fi
    echo "Installing yarn"
    npm install --global yarn
else
    echo "yarn detected"
fi

RCfile=$HOME/.bashrc
if [ "$SHELL" = "/bin/sh" ]; then
    RCfile="$HOME/.profile"
fi

if [ `grep -q "OPEN_AI_KEY" $RCfile` ]; then
  echo "OpenAI API key detected. If you need to change this, edit the OPENAI_API_KEY in $RCfile."
else
  echo "Enter your OpenAI license key below. You can get your key by going to https://platform.openai.com/account/api-keys and hitting ''Create new secret key''"
  read LICENSE_KEY
  echo "export OPENAI_API_KEY=$LICENSE_KEY" >> $RCfile
fi

if [ ! `grep -q "alias gpt=" $RCfile` ]; then
  echo "alias gpt='python3 `pwd`/api/gpt_command_prompt.py'" >> $RCfile
  echo "Command 'gpt' is now defined."
fi

if [ ! `grep -q "alias gtp=" $RCfile` ]; then
  echo "alias gtp='python3 `pwd`/api/gpt_command_prompt.py'" >> $RCfile
fi

if [ ! `grep -q "alias gpte=" $RCfile` ]; then
  echo "alias gpte='python3 `pwd`/api/gpt_command_prompt_edit_loop.py'" >> $RCfile
  echo "Command 'gpte' is now defined."
fi

if [ ! `grep -q "alias gtpe=" $RCfile` ]; then
  echo "alias gtpe='python3 `pwd`/api/gpt_command_prompt_edit_loop.py'" >> $RCfile
fi
source $RCfile

fi #continuing2
fi #continuing1
