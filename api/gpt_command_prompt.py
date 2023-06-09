import os, sys
import json
import openai
import argparse
from gpt import GPT
#from gpt import Example

#example: 
#gpt "my prompt" [epilog prompt] [-n max length]
#gpt -f file1 file2

#TODO: 
#-[ ] get rid of the GPT library... what's it even for?  Clear out all the junk from the fork
#-[ ] make token max proportional to which model is used 
#-[ ] Automate expansion of word count
#-[ ] enable example file
#-[x] make a sensible integration of chatGPT into the command system
#-[ ] integrate conversation into the chatGPT option
#-[ ] integrate older models since they have much higher token rate limits.
#-[ ] check that max tokens isn't 

#todo: make a conversation system -- finally, a use for standrd io
#automated conversatoin mode

#Argparse 
#argparse documentation: https://docs.python.org/3/library/argparse.html
parser = argparse.ArgumentParser(description='''A basic command line parser for GPT3''', epilog = '''Command-line interface written by Anthony Barker, 2022. The main strucutre was written primarily by Shreya Shankar, Bora Uyumazturk, Devin Stein, Gulan, and Michael Lavelle''',prog="gpt_command_prompt")

parser.add_argument("prompt", nargs='?', help="Prolog prompt string")
parser.add_argument("prompt_epilog", nargs='?', help="Epilog prompt string") #broken

parser.add_argument("-n", dest="max_tokens", type=int, help="Maximum token count (sort-of like word-count) of the AI responce", default = -1) 
parser.add_argument("-f","--file", nargs='+', help="Prompt file, will not be used for tokens counts") 
parser.add_argument("-o", dest="out", help="Responce output file", default = "gptoutput.txt") 
parser.add_argument('-e', '--echo', action='store_true', help='Print Prompt as well as responce')

parser.add_argument('--old', action='store_true', help='Use GPT-3 instead of GPT-3.5-turbo')
parser.add_argument('--verbose', action='store_true', help='Spew everything')
parser.add_argument('-d', '--disable', action='store_true', help='Does not send command to GPT-3, used for prompt design and development')

parser.add_argument('-c', '--code', action='store_true', help='Uses the code_davinci_002 model to optomize code quality')
parser.add_argument("--top_p", type=float, help="top_p parameter. Controls diversity via nucleus sampling. 0.5 means half of all likelihood-weighted options are considered. Clamped to [0,1]", default = 1.0) 
parser.add_argument("--temp", type=float, help="temperature parameter. Controls randomness. Lowering results in less random completions. As the temperature approaches zero, the model will become deterministic and repetitive. Clamped to [0,1]", default = 0) 
parser.add_argument("-q", dest="frequency_penalty", type=float, help="frequency_penalty parameter. How much to penalize new tokens based on their existing frequency in the text so far. Decreases the model's likelihood of repeating the same line verbatim. Clamped to [0,2]", default = 0) 
parser.add_argument("-p", dest="presence_penalty", type=float, help="presence_penalty parameter. How much to penalize new tokens based on whether they appear in the text so far. Increaces the model's likelihood to talk about new topics. Clamped to [0,2]", default = 0) 
parser.add_argument("-v", "--version", action='version', version='%(prog)s 0.2.2') 
#best of parameter, an int.
args = parser.parse_args() 


def clamp(num, minval,maxval):
	return max(min(num, maxval),minval)

#Model parameter prototypes: 
Prompt = ""
Max_Tokens = -1
Top_p= clamp(args.top_p ,0.0,1.0) #1.0
Temp = clamp(args.temp ,0.0,1.0) #0
Frequency_penalty = clamp(args.frequency_penalty ,0.0,2.0) #0
Presence_penalty = clamp(args.presence_penalty ,0.0,2.0) #0
verbose = False

#Input Ingestion
if args.max_tokens:
	Max_Tokens = args.max_tokens

verbose |= args.echo or args.disable or args.verbose

Model = "gpt-3.5-turbo"
use_chatGPT = True 
model_token_max = 4096 #for the table, see https://platform.openai.com/docs/models/gpt-4
if args.old:
    Model = "gpt-3.5-turbo"
    use_chatGPT  = False
    model_token_max = 4097 #yeah, weird, but that's what they say
elif args.code:
    Model = "code-davinci-002"
    use_chatGPT  = False
    model_token_max = 8001 

if args.prompt:
    Prompt = args.prompt
if args.file: #if args.file != "dud": 
    for fname in args.file:
        if Prompt == "":
            with open(fname, 'r', errors='ignore') as fin:
                Prompt = fin.read()#encoding="utf-8")
        else: 
            with open(fname, 'r', errors='ignore') as fin:
                Prompt += '\n' + fin.read() 
if args.prompt_epilog:
    Prompt += '\n' + args.prompt_epilog
if Prompt == "":
    Prompt = "In a bash program that calls GPT-3, the user forgot to input a prompt string. Say something cute to remind the user to write a prompt string "
    Top_p = 0.5
    Temp = 0.7


if args.verbose:
    if Max_Tokens >= 0:
        print("Max_Tokens ",Max_Tokens )
    else:
        print("Max_Tokens not set")
    print("Top_p",Top_p)
    print("Temp",Temp)
    print("Frequency_penalty ",Frequency_penalty )
    print("Presence_penalty ",Presence_penalty )

if verbose:
    print("Prompt: ")
    print(Prompt)

mac_mode = False
if sys.platform == "darwin":
    mac_mode = True

##OTHER GPT3 Examples##
#gpt = GPT(engine="davinci", temperature=0.5, max_tokens=Max_Tokens)

#Few-shot training examples:
#gpt.add_example(Example('Fetch unique values of DEPARTMENT from Worker table.','Select distinct DEPARTMENT from Worker;'))
#gpt.add_example(Example('Print the first three characters of FIRST_NAME from Worker table.', 'Select substring(FIRST_NAME,1,3) from Worker;'))

#print("Responce ala davinci:")
#print(gpt.get_top_reply(Prompt))
#output = gpt.submit_request(prompt) #output is json 
#print(output.choices[0].text)

#print("Example 2")
#prompt = "Tell me the count of employees working in the department HR."
#print(gpt.get_top_reply(prompt))

if not args.disable:
    openai.api_key = os.getenv("OPENAI_API_KEY")

    if use_chatGPT:
        if Max_Tokens >= 0:
            response = openai.ChatCompletion.create(
                model=Model, 
                messages=[{"role": "user", "content": Prompt}],
                temperature=Temp,
                max_tokens=Max_Tokens,
                top_p=Top_p,
                frequency_penalty=Frequency_penalty,
                presence_penalty=Presence_penalty
                )
        else:
            response = openai.ChatCompletion.create(
                model=Model, 
                messages=[{"role": "user", "content": Prompt}],
                temperature=Temp,
                top_p=Top_p,
                frequency_penalty=Frequency_penalty,
                presence_penalty=Presence_penalty
                )
    else:
        if Max_Tokens >= 0:
            response = openai.Completion.create(
                model=Model,
                prompt=Prompt,
                temperature=Temp,
                max_tokens=Max_Tokens,
                top_p=Top_p,
                frequency_penalty=Frequency_penalty,
                presence_penalty=Presence_penalty
                )
        else:
            response = openai.Completion.create(
                model=Model,
                prompt=Prompt,
                temperature=Temp,
                top_p=Top_p,
                frequency_penalty=Frequency_penalty,
                presence_penalty=Presence_penalty
                )
    if verbose:
        print("Response:")
    if args.verbose:
        print(response)
    elif use_chatGPT:
        print(response.choices[0].message.content)
    else:
        print(response.choices[0].text) 
    
    if args.out: 
        with open(args.out,'w') as fout:
            if use_chatGPT:
                fout.write(response.choices[0].message.content)
            else:
                fout.write(response.choices[0].text) 
    
    if mac_mode:
        os.system(f"open -a textEdit {args.out} &")
    else:
        os.system("/mnt/c/windows/system32/notepad.exe "+args.out+" &")

