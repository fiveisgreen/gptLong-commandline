#!/bin/csh

continuing=true
if ( ! `which python3` ) then
then
    while( {true} )
        read -p "Python3 not detected. Would you like to automatically install python 3.6 now with sudo apt-get? (y/n):" yn
        switch ($yn)
            case [Yy]: 
                sudo apt update -y && sudo apt-get install python3.6 -y; break;
            case [Nn]: 
                continuing=false; break;
            default:
               echo "Please answer yes (y/Y) or no (n/N)."; breaksw
        endsw
    end
endif

if ( "$continuing" = true ) then

if ( ! `which pip` ) then
    while( {true} )
        read -p "pip not detected. Would you like to automatically install python3-pip now with sudo apt-get? (y/n):" yn
        switch ($yn)
            case [Yy]: 
                sudo apt update -y && sudo apt-get install python3-pip -y; break;
            case [Nn]: 
                continuing=false; break;
            default:
               echo "Please answer yes (y/Y) or no (n/N)."; breaksw
        endsw
    end
endif

if ( "$continuing" = true ) then

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

endif #continuing2
endif #continuing1
