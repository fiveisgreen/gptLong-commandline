#!/bin/bash

pip install openai

if [ grep -q "OPEN_AI_KEY" ~/.bashrc ]; then
  echo "OpenAI API key detected. If you need to change this, edit the OPENAI_API_KEY in ~/.bashrc."
else
  echo "Enter your OpenAI license key below. You can get your key by going to https://platform.openai.com/account/api-keys and hitting ''Create new secret key''"
  read LICENSE_KEY
  echo "export OPENAI_API_KEY=$LICENSE_KEY" >> ~/.bashrc
fi

if [ ! grep -q "alias gpt=" ~/.bashrc ]; then
  echo "alias gpt='python3 `pwd`/api/gpt_command_prompt.py'" >> ~/.bashrc
  echo "Command 'gpt' is now defined."
fi

if [ ! grep -q "alias gtp=" ~/.bashrc ]; then
  echo "alias gtp='python3 `pwd`/api/gpt_command_prompt.py'" >> ~/.bashrc
fi

if [ ! grep -q "alias gpte=" ~/.bashrc ]; then
  echo "alias gpte='python3 `pwd`/api/gpt_command_prompt_edit_loop.py'" >> ~/.bashrc
  echo "Command 'gpte' is now defined."
fi

if [ ! grep -q "alias gtpe=" ~/.bashrc ]; then
  echo "alias gtpe='python3 `pwd`/api/gpt_command_prompt_edit_loop.py'" >> ~/.bashrc
fi
source ~/.bashrc

