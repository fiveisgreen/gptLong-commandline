# Command-line Interface 
This is a fork of the GPT-3 Sandbox described more below. This fork adds python based shell commands for interacting with OpenAI models from a linux the command line (developed on WSL2/Ubuntu20.04 on Windows 10). 

Two commands are made available `gpt` and `gpte`. `gpte` can be used to edit arbitrarily long text files according to an edit prompt, by chunking the long file, calling the edit/system prompt along with the chunk, and then stitching the resut. `gpt` calls a basic single-prompt single-answer interaction, GPT-3 style. 

For both, use the -c or --code options to change to code oriented models. 

## Setup 
gpte command calls a file difference tool, which can be Meld, vimdiff, or diff. I recommend installing [Meld](https://meld.app/). Then have to set the location of the Meld executable in api/gpt\_command\_prompt\_edit\_loop.py on line 12.

`git clone https://github.com/fiveisgreen/gptLong-commandline.git`

`cd gptLong-commandline`

Get your [OpenAI API key](https://platform.openai.com/account/api-keys) ready and call the setup script. 

Check which shell you're using

`echo $SHELL`

For bash and sh:

`source setup.sh`

(For tcsh and csh you can run `source setup.csh`. This is almost certainly unnecessary and you should always be able to run setup.sh no matter which shell you're using)

Dependencies for GPT-3 sandbox should be installed by these. If there's any trouble installing the dependencies, see the Requirements section below.

### Test the installation: 
source `run_tests.sh`

## Usage: The gpt command 
The `gpt` command takes in a prompt and produces a single result. The prompt can have multiple parts, and can mix command-line text and multiple file prompt components. Call gpt -h for full usage details. 

### Examples:  

> gpt "What is the Capital of France?" 

Most basic use, prompts text-davinci-003, aka GPT-3.

> gtp "Write a hiku about being put on call holding" --temp 0.9 -p 2 -q 2

Manually set temperature, presence, and frequency penalties. The gtp command is also defined for typo correction, and is identical to gpt.

> gpt "What is the Capital of France?" -o outputFile.txt --echo

-o writes the responce to outputFile.txt, and since the --echo/-e option is used, the prompt is also echoed into that file. 

> gpt -f promptFile1.txt promptFile2.txt -o outputFile.txt "My prompt prefix" "My prompt suffix" --disable --verbose

This will take as prompt the prompt prefix, then the contents of the prompt files, then the suffix. All are seperated by \n in the final prompt. This is useful for engineering a prompt structure that frames some content stored in the files. There is no limit to the number of prompt files other than the model's token limit. 
--disable/-d prevent the command from actually calling GPT. Use this for prompt command development. --verbose prints what the script is doing in detail. 

> gpt -f myBuggyCode.cpp -c "Serve as an expert software test engineer and identify bugs in the following code:" 

Turn on code mode and use the code-davinci-002 model. 


## Usage: The gpte command 
The `gpte` is centered around file editing. It takes two prompts: an instruction prompt and a body prompt. 

### Examples:
> gtpe "my instruction prompt" -f bodyFile [-o outfile]
> gpte "my instruction prompt" "my body prompt to edit"
> gtpe -f bodyFile1 -i instrFile1 instrFile2 [-o outfile]

IO Options:
Directly provide a text string, which becomes the instruction prompt.
* -i filenames  provide an instruction prompt from file. Can be more than one file. These appends to the commandline instruction string.
* -f filename   The body prompt from file. 
* -o filename   The output. If no -o options is give, this writes back to the -f body prompt file.

#### Model Choice Options: 
* (Default model is gpt-3.5-turbo, aka chatGPT)
* -16k          Use the new gpt-3.5-turbo-16k model, which has 4x the context length of gpt-3.5-turbo
* -c --code     Change to a code oriented model code-davinci-edit-001
* -e --edit     Change to the text-editing oriented model text-davinci-edit-001.
* --old         switch the model from chatGPT (gpt-3.5-turbo) with system and body prompts to a GPT-3 model with a merged instruction and body.
*    --old = --old 1       text-davinci-003
*    --old 2    text-davinci-002
*    --old 3    Curie (text-curie-001)
*    --old 4    Babbage (text-babbage-001)
*    --old 5    Ada (text-ada-001)
Using older models is often great since they're much faster, much cheaper, and often are good enough. 

#### Other Important Option:
* -h --help     Shows a description of all options.
* -n MAX\_TOKENS\_IN  Allows you to limit the number of tokens in each chunk of text fed to the model. Use lower values (~300) if the model is truncating the output or if there's an error of exceeding the model's token limit. 
* --echo        prints prompt and responce to terminal
* -v --verbose  turn on verbose printing (Coming soon: making this an int verbosity level)
* -d --disable  disables GTP-3 call for debugging
* -v --version  print version.
Coming soon: 
test mode for trying out a prompt before feeding a large file through a model. 

## Troubleshooting 
### AuthenticaionError
This may indicate a probem with the API key, but I still don't understand this error category. 
### RateLimitError
"openai.error.RateLimitError: The server had an error while processing your request. Sorry about that!"
Seems to have to do with sending a lot of API calls quickly, particularly using gpte, which chunks large documents and can make many API calls quickly. 


## Credits:
This repository started as a branch of GPT-3 Sandbox, but no longer uses their developments. Many thanks to 
the following authors for their significant contributions that got this project started: 

* Shreya Shankar
* Bora Uyumazturk
* Devin Stein
* Gulan
* Michael Lavelle


