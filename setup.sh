#!/bin/bash

continuing=true
#Make sure the shell is set correctly
if [[ $SHELL = /bin/csh || $SHELL = /bin/tcsh ]]; then
    continue=false
    source setup.csh
elif [[ ! ( $SHELL = /bin/sh || $SHELL = /bin/bash ) ]]; then
    echo "shell `$SHELL` is not supported. Try bash, csh, or tcsh."
    continue=false
fi


if [ "$continuing" = true ]; then

if ! command -v python3 &> /dev/null
then
    while true; do
        read -p "Python3 not detected. Would you like to automatically install python 3.8 now with sudo apt-get? (y/n):" yn
        case $yn in
            [Yy]* ) sudo apt update -y && sudo apt-get install python3.8 -y; break;;
            [Nn]* ) continuing=false; break;;
            * ) echo "Please answer yes (y/Y) or no (n/N).";;
        esac
    done
fi

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
else
    echo "Updating pip"
    python3 -m pip install --upgrade pip
fi

if [ "$continuing" = true ]; then

pip install --upgrade openai

if ! command -v yarn &> /dev/null 
then
    echo "yarn not detected. Installing..."
    if ! command -v npm &> /dev/null
    then
        echo "nvm not detected, installing it:"
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash
    else
        echo "Updating npm"
        npm update -g npm
    fi
    echo "Installing yarn"
    npm install --global yarn
else
    echo "yarn detected, updating it"
    npm update -g yarn
fi

RCfile=$HOME/.bashrc
if [ "$SHELL" = "/bin/sh" ]; then
    RCfile="$HOME/.profile"
fi

if [ ! -f $RCfile ]; then
    touch $RCfile
fi

if [ `grep -q "OPEN_AI_KEY" $RCfile` ]; then
  echo "OpenAI API key detected. If you need to change this, edit the OPENAI_API_KEY in $RCfile."
else
  echo ""
  echo "  .-.     .-.     .-.     .-.     .-.     .-.     .-.     .-.     .-.     .-.   "
  echo ".'   \`._.'   \`._.'   \`._.'   \`._.'   \`._.'   \`._.'   \`._.'   \`._.'   \`._.'   \`. "
  echo ""
  echo "Now your OpenAI key is needed. You can get your key by going to https://platform.openai.com/account/api-keys and hitting ''Create new secret key''"
  echo ""
  echo "PASTE YOUR OPENAI KEY"
  read LICENSE_KEY
  echo "export OPENAI_API_KEY=$LICENSE_KEY" >> $RCfile
fi

if [ ! `grep -q "alias chatgpt=" $RCfile` ]; then
  echo "alias chatgpt='python3 `pwd`/api/chatGPT.py'" >> $RCfile
  echo "Command 'chatgpt' is now defined."
fi
if [ ! `grep -q "alias chatgtp=" $RCfile` ]; then
  echo "alias chatgtp='python3 `pwd`/api/chatGPT.py'" >> $RCfile
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
echo "Reloading shell startup configuration"
source $RCfile

echo "The system variable OPEN_AI_KEY is now"
echo $OPEN_AI_KEY

fi #continuing2
fi #continuing1
fi #continuing0
