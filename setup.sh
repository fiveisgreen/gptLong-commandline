#!/bin/bash

continuing=true
#if [[ $SHELL = /bin/csh || $SHELL = /bin/tcsh ]]; then
#    continue=false
#    source setup.csh
#elif [[ ! ( $SHELL = /bin/sh || $SHELL = /bin/bash ) ]]; then
#    echo "shell `$SHELL` is not supported. Try bash, csh, or tcsh."
#    continue=false
#fi

#if [ "$continuing" = true ]; then

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

if [[ $(grep -c "OPENAI_API_KEY" $RCfile) -gt 0 ]]; then
  echo "OpenAI API key detected: $OPENAI_API_KEY. If you need to change this, edit the OPENAI_API_KEY in $RCfile."
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

if [[ $(grep -c "alias chatgpt=" $RCfile) -le 0 ]]; then
  echo "alias chatgpt='python3 `pwd`/api/chatGPT.py'" >> $RCfile
  echo "Command 'chatgpt' is now defined."
else
  echo "chatgpt command found."
  grep "alias chatgpt=" $RCfile
fi
if [[ $(grep -c "alias chatgtp=" $RCfile) -le 0 ]]; then
  echo "alias chatgtp='python3 `pwd`/api/chatGPT.py'" >> $RCfile
fi

if [[ $(grep -c "alias gpt=" $RCfile) -le 0 ]]; then
  echo "alias gpt='python3 `pwd`/api/gpt_command_prompt.py'" >> $RCfile
  echo "Command 'gpt' is now defined."
else
    echo "gpt command found."
    grep "alias gpt=" $RCfile
fi

if [[ $(grep -c "alias gtp=" $RCfile) -le 0 ]]; then
  echo "alias gtp='python3 `pwd`/api/gpt_command_prompt.py'" >> $RCfile
fi

if [[ $(grep -c "alias gpte=" $RCfile) -le 0 ]]; then
  echo "alias gpte='python3 `pwd`/api/gpt_command_prompt_edit_loop.py'" >> $RCfile
  echo "Command 'gpte' is now defined."
else
    echo "gpte command found."
    grep "alias gpte=" $RCfile
fi

if [[ $(grep -c "alias gtpe=" $RCfile) -le 0 ]]; then
  echo "alias gtpe='python3 `pwd`/api/gpt_command_prompt_edit_loop.py'" >> $RCfile
fi
echo "Reloading shell startup configuration"
source $RCfile

echo "The system variable OPENAI_API_KEY is now"
echo $OPENAI_API_KEY

fi #continuing2
fi #continuing1
#fi #continuing0
