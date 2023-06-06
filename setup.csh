#!/bin/csh
if ( ! `which python3` ) then
    echo "Python3 not detected, install python with:"
    echo "sudo apt update -y && sudo apt-get install python3.6 -y"
    exit 1
endif

if ( ! `which pip` ) then
    echo "pip not found. Install pip with:"
    echo "sudo apt update -y && sudo apt-get install python3-pip -y"
    exit 1
endif

pip install openai

if ( ! `which yarn` ) then
    echo "yarn not detected, Installing..."
    if ( ! `which npm` ) then
        echo "nvm not detected, installing it:"
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | csh
    endif
    echo "Installing yarn"
    npm install --global yarn
else
    echo "yarn detected"
endif

set RCfile = $HOME/.cshrc
if ( "$SHELL" == "/bin/tcsh" ) then
    set RCfile = $HOME/.tcshrc
endif

if ( `grep -q "OPEN_AI_KEY" ~/.cshrc` ) then
  echo "OpenAI API key detected. If you need to change this, edit the OPENAI_API_KEY in $RCfile."
else
  echo "Enter your OpenAI license key below. You can get your key by going to https://platform.openai.com/account/api-keys and hitting ''Create new secret key''"
  set LICENSE_KEY = $<
  echo "setenv OPENAI_API_KEY $LICENSE_KEY" >> $RCfile
endif

if ( ! `grep -q "alias gpt=" $RCfile` ) then
  echo "alias gpt 'python3 `pwd`/api/gpt_command_prompt.py'" >> $RCfile
  echo "Command 'gpt' is now defined."
endif

if ( ! `grep -q "alias gtp=" $RCfile` ) then
  echo "alias gtp='python3 `pwd`/api/gpt_command_prompt.py'" >> $RCfile
endif

if ( ! `grep -q "alias gpte=" $RCfile` ) then
  echo "alias gpte='python3 `pwd`/api/gpt_command_prompt_edit_loop.py'" >> $RCfile
  echo "Command 'gpte' is now defined."
endif

if ( ! `grep -q "alias gtpe=" $RCfile` ) then
  echo "alias gtpe='python3 `pwd`/api/gpt_command_prompt_edit_loop.py'" >> $RCfile
endif
source $RCfile

