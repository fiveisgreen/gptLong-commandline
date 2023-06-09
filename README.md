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

Important Option Flags:
* -g --gtp3     switch the model from edit mode (text-davinci-edit-001) with 2 prompts to text-davinci-003 wiht a merged instruction and body.
* -c --code     switch engine to code mode code-davinci-edit-001 (code-davinci-002 if combined with -g).
* -e --echo     prints prompt and responce to terminal
* -v --verbose  turn on verbose printint
* -d --disable  disables GTP-3 call for debugging
* -v --version  print version.

## Troubleshooting 
### AuthenticaionError
This may indicate a probem with the API key, but I still don't understand this error category. 
### RateLimitError
"openai.error.RateLimitError: The server had an error while processing your request. Sorry about that!"
Seems to have to do with sending a lot of API calls quickly, particularly using gpte, which chunks large documents and can make many API calls quickly. 

---
---

# GPT-3 Sandbox: Turn your ideas into demos in a matter of minutes

Initial release date: 19 July 2020

Note that this repository is not under any active development; just basic maintenance.

## Description

The goal of this project is to enable users to create cool web demos using the newly released OpenAI GPT-3 API **with just a few lines of Python.** 

This project addresses the following issues:

1. Automatically formatting a user's inputs and outputs so that the model can effectively pattern-match
2. Creating a web app for a user to deploy locally and showcase their idea

Here's a quick example of priming GPT to convert English to LaTeX:

```
# Construct GPT object and show some examples
gpt = GPT(engine="davinci",
          temperature=0.5,
          max_tokens=100)
gpt.add_example(Example('Two plus two equals four', '2 + 2 = 4'))
gpt.add_example(Example('The integral from zero to infinity', '\\int_0^{\\infty}'))
gpt.add_example(Example('The gradient of x squared plus two times x with respect to x', '\\nabla_x x^2 + 2x'))
gpt.add_example(Example('The log of two times x', '\\log{2x}'))
gpt.add_example(Example('x squared plus y squared plus equals z squared', 'x^2 + y^2 = z^2'))

# Define UI configuration
config = UIConfig(description="Text to equation",
                  button_text="Translate",
                  placeholder="x squared plus 2 times x")

demo_web_app(gpt, config)
```

Running this code as a python script would automatically launch a web app for you to test new inputs and outputs with. There are already 3 example scripts in the `examples` directory.

You can also prime GPT from the UI. for that, pass `show_example_form=True` to `UIConfig` along with other parameters.

Technical details: the backend is in Flask, and the frontend is in React. Note that this repository is currently not intended for production use.

## Background

GPT-3 ([Brown et al.](https://arxiv.org/abs/2005.14165)) is OpenAI's latest language model. It incrementally builds on model architectures designed in [previous](https://arxiv.org/abs/1706.03762) [research](https://arxiv.org/abs/1810.04805) studies, but its key advance is that it's extremely good at "few-shot" learning. There's a [lot](https://twitter.com/sharifshameem/status/1282676454690451457) [it](https://twitter.com/jsngr/status/1284511080715362304?s=20) [can](https://twitter.com/paraschopra/status/1284801028676653060?s=20) [do](https://www.gwern.net/GPT-3), but one of the biggest pain points is in "priming," or seeding, the model with some inputs such that the model can intelligently create new outputs. Many people have ideas for GPT-3 but struggle to make them work, since priming is a new paradigm of machine learning. Additionally, it takes a nontrivial amount of web development to spin up a demo to showcase a cool idea. We built this project to make our own idea generation easier to experiment with.

This [developer toolkit](https://www.notion.so/API-Developer-Toolkit-49595ed6ffcd413e93ebff10d7e70fe7) has some great resources for those experimenting with the API, including sample prompts.

## Requirements

Coding-wise, you only need Python. But for the app to run, you will need:

* API key from the OpenAI API beta invite
* Python 3
* `yarn`
* Node 16

Instructions to install Python 3 are [here](https://realpython.com/installing-python/), instructions to install `yarn` are [here](https://classic.yarnpkg.com/en/docs/install/#mac-stable) and we recommend using nvm to install (and manage) Node (instructions are [here](https://github.com/nvm-sh/nvm)).

## Setup

First, clone or fork this repository. Then to set up your virtual environment, do the following:

1. Create a virtual environment in the root directory: `python -m venv $ENV_NAME`
2. Activate the virtual environment: ` source $ENV_NAME/bin/activate` (for MacOS, Unix, or Linux users) or ` .\ENV_NAME\Scripts\activate` (for Windows users)
3. Install requirements: `pip install -r api/requirements.txt`
4. To add your secret key: create a file anywhere on your computer called `openai.cfg` with the contents `OPENAI_KEY=$YOUR_SECRET_KEY`, where `$YOUR_SECRET_KEY` looks something like `'sk-somerandomcharacters'` (including quotes). If you are unsure what your secret key is, navigate to the [API Keys page](https://beta.openai.com/account/api-keys) and click "Copy" next to a token displayed under "Secret Key". If there is none, click on "Create new secret key" and then copy it.
5. Set your environment variable to read the secret key: run `export OPENAI_CONFIG=/path/to/config/openai.cfg` (for MacOS, Unix, or Linux users) or `set OPENAI_CONFIG=/path/to/config/openai.cfg` (for Windows users)
6. Run `yarn install` in the root directory

If you are a Windows user, to run the demos, you will need to modify the following line inside `api/demo_web_app.py`:
`subprocess.Popen(["yarn", "start"])` to `subprocess.Popen(["yarn", "start"], shell=True)`.

To verify that your environment is set up properly, run one of the 3 scripts in the `examples` directory:
`python examples/run_latex_app.py`.

A new tab should pop up in your browser, and you should be able to interact with the UI! To stop this app, run ctrl-c or command-c in your terminal.

To create your own example, check out the ["getting started" docs](https://github.com/shreyashankar/gpt3-sandbox/blob/master/docs/getting-started.md).

## Interactive Priming

The real power of GPT-3 is in its ability to learn to specialize to tasks given a few examples. However, priming can at times be more of an art than a science. Using the GPT and Example classes, you can easily experiment with different priming examples and immediately see their GPT on GPT-3's performance. Below is an example showing it improve incrementally at translating English to LaTeX as we feed it more examples in the python interpreter: 

```
>>> from api import GPT, Example, set_openai_key
>>> gpt = GPT()
>>> set_openai_key(key)
>>> prompt = "integral from a to b of f of x"
>>> print(gpt.get_top_reply(prompt))
output: integral from a to be of f of x

>>> gpt.add_example(Example("Two plus two equals four", "2 + 2 = 4"))
>>> print(gpt.get_top_reply(prompt))
output:

>>> gpt.add_example(Example('The integral from zero to infinity', '\\int_0^{\\infty}'))
>>> print(gpt.get_top_reply(prompt))
output: \int_a^b f(x) dx

``` 

## Contributions

We actively encourage people to contribute by adding their own examples or even adding functionalities to the modules. Please make a pull request if you would like to add something, or create an issue if you have a question. We will update the contributors list on a regular basis.

Please *do not* leave your secret key in plaintext in your pull request!

## Authors

The following authors have committed 20 lines or more (ordered according to the Github contributors page):

* Shreya Shankar
* Bora Uyumazturk
* Devin Stein
* Gulan
* Michael Lavelle


