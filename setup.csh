#!/bin/csh

set continuing = true
if ( `which python3` == "") then
    while( 1 )
        echo "Python3 not detected. Would you like to automatically install python 3.8 now with sudo apt-get? (y/n):"
        set yn = $<
        switch ($yn)
            case [Yy]: 
                sudo apt update -y && sudo apt-get install python3.8 -y; break;
            case [Nn]: 
                set continuing = false; break;
            default:
               echo "Please answer yes (y/Y) or no (n/N)."; breaksw
        endsw
    end
endif

if ( "$continuing" == true ) then

if ( `which pip` == "" ) then
    while( 1 )
        echo "pip not detected. Would you like to automatically install python3-pip now with sudo apt-get? (y/n):" 
        set yn = $<
        #read -p "pip not detected. Would you like to automatically install python3-pip now with sudo apt-get? (y/n):" yn
        switch ($yn)
            case [Yy]: 
                sudo apt update -y && sudo apt-get install python3-pip -y; break;
            case [Nn]: 
                set continuing = false; break;
            default:
               echo "Please answer yes (y/Y) or no (n/N)."; breaksw
        endsw
    end
else
    echo "Updating pip"
    python3 -m pip install --upgrade pip
endif

if ( "$continuing" == true ) then

pip install --upgrade openai

if ( `which yarn` == "") then
    echo "yarn not detected, Installing..."
    if ( `which npm` == "") then
        echo "nvm not detected, installing it:"
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | csh
    else
        echo "Updating npm"
        npm update -g npm
    endif
    echo "Installing yarn"
    npm install --global yarn
else
    echo "yarn detected, updating it"
    npm update -g yarn
endif

set RCfile = $HOME/.cshrc
if ( "$SHELL" == "/bin/tcsh" ) then
    set RCfile = $HOME/.tcshrc
endif

if (! -e $RCfile) then
    touch $RCfile
endif

if ( `grep -q "OPEN_AI_KEY" ~/.cshrc` ) then
  echo "OpenAI API key detected. If you need to change this, edit the OPENAI_API_KEY in $RCfile."
else
  echo ""
  echo "  .-.     .-.     .-.     .-.     .-.     .-.     .-.     .-.     .-.     .-.   "
  echo ".'   '._.'   '._.'   '._.'   '._.'   '._.'   '._.'   '._.'   '._.'   '._.'   '. "
  echo ""
  echo "Now your OpenAI key is needed. You can get your key by going to https://platform.openai.com/account/api-keys and hitting ''Create new secret key''"
  echo ""
  echo "PASTE YOUR OPENAI KEY"
  set LICENSE_KEY = $<
  echo "setenv OPENAI_API_KEY $LICENSE_KEY" >> $RCfile
endif

if ( ! `grep -q "alias chatgpt=" $RCfile` ) then
  echo "alias chatgpt 'python3 `pwd`/api/chatGPT.py'" >> $RCfile
  echo "Command 'chatgpt' is now defined."
endif
if ( ! `grep -q "alias chatgtp=" $RCfile` ) then
  echo "alias chatgtp='python3 `pwd`/api/chatGPT.py'" >> $RCfile
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
echo "Reloading shell startup configuration"
source $RCfile

echo "The system variable OPEN_AI_KEY is now"
echo $OPEN_AI_KEY

endif #continuing2
endif #continuing1
