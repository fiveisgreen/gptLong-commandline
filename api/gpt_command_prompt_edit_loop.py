import os, sys
import json
import openai
import argparse
import token_cut_light
from gpt import GPT
from math import ceil
import time

""" #################### USAGE AND EXAMPLES ###########################

###### Examples ######

$ gtpe "my instruction prompt" -f body_file [-o outfile]
$ gpte "my instruction prompt" "my body prompt to edit" 
$ gtpe -f body_file1 -i instr_file1 instr_file2 [-o outfile]

####### FUll Usage #######
$ gtpe ["instructions"] ["body epilog"] [-f body.txt] [-i instruction1.txt instrcution2.txt] [-o outfile.txt] [params] [flags]


positional arguments:
  prompt_inst           Instruction prompt string. If both this and -i files are give, this goes after the file contents.
  prompt_body           Body prompt string. If both this and -f files are give, this goes after the file contents.

IO:
#   Just supply a text string and it becomes appended to the front of the instruction prompt 
#  -i INSTRUCTION_FILES [INSTRUCTION_FILES ...]
                        Prompt files, to be used for edit instructions.
#  -f FILES, --files FILES
                        Prompt file of body text to be edited.
#  -o OUT                Responce output file

Model Selectors:
#  -16k, --16k           Use gpt-3.5-turbo-16k, with 4x the context window of the default gpt-3.5-turbo. This flag overrides -c/--code,
                        -e/--edit, and --old
#  -e, --edit            Uses the text-davinci-edit-001 model, which is older but oriented around text editing
#  -c, --code            Uses the code-davinci-002 model to optomize code quality, and uses merged instruction and body and double the
                        max input tokens. If combined with -e, uses code-davinci-edit-001.
#  --old [OLD]           Use older models with merged instructions and prompt for speed and cost. OLD: {no_arg = 1:text-davinci-003;
                        2:text-davinci-002; 3:Curie; 4: Babbage; 5+: Ada}

Flags:
#  -h, --help   show all options and exit
# -e --edit     switch engine to an edit oriented model
# -c --code     switch engine to code mode
# --old         switch engine from edit mode to merged prompt mode with instruction prolog.
# --echo     prints prompt and responce to terminal
# --verbose  turn on verbose printint
# -d --disable  disables GTP-3 call for debugging
# -v --version  print version.

Optional Model Parameters
-n --max_tokens_in  #max tokens of prompt chunk, clipped between [25, model's maximum input] 
--max_tokens_out #max tokens of the responce, used to prevent runaway. Default is 20,000.
--top_p [0..1]  #Controls diversity. Default=1. 
--temp [0..1]   #Controls ramdomness, 0 = deterministic and repetitive.
-p [0..2]       #presence_penalty, turn up encourages discussion diversity. Use only with -g.
-q [0..2]       #frequency_penalty, turn up discourages repetition. Use only with -g. 

TODO:
    - [x] fix the max_tokens_out mess
    - [x]     does it fix the chunking problem.
    - [x] make max input tokens a commandline parameter to control the chunk length
    - [x] update the Usage in this file
    - [x] update usage Examples in readme
    - [x] Test if other models still work
    - [x] input tokens model dependent
    - [x] use gpt-3.5-turbo
    - [x] Make use of openAI's updates to gpt-3.5-turbo-16k
    - [ ] Colorize verbose output
    - [ ]     Add library install to the setup script
    - [ ] Make the guts of this a function. 
    - [x] Add time estimate
    - [x] make old integer parameterizable, and able to run ada, babage etc.
    - [ ] Make verbose into verbosity, an int from 0 .. 9
    - [x] Add price estimate and warnings
    - [ ] Add rate limiter so you don't get rate errors. 
        Overview: https://platform.openai.com/docs/guides/rate-limits/overview
        cookbook: https://github.com/openai/openai-cookbook/blob/main/examples/How_to_handle_rate_limits.ipynb
        avoidance script: https://github.com/openai/openai-cookbook/blob/main/examples/api_request_parallel_processor.py
    - [ ] Add parallel processing of chunks, see https://github.com/openai/openai-cookbook/blob/main/examples/api_request_parallel_processor.py
    - [ ] add chunk limiter to test output. Maybe just a "test" mode
    - [x] Gracefully check that all filex exist before doing anything else.
    - [ ] Make a compare tool to compare the output of different models
    - [ ] Migrate these improvements to the gpt command
"""


"""SETTINGS"""
meld_exe_file_path = "/mnt/c/Program Files/Meld/MeldConsole.exe" #don't use backslashes before spaces. Don't worry about this if you're on mac. 
mac_mode = False
if sys.platform == "darwin": 
    mac_mode = True

#list of all encoding options https://docs.python.org/3/library/codecs.html#standard-encodings
Encoding = "utf8" #
#Encoding = "latin1" #ok regardless of utf8 mode, but tends to wrech singla and double quotation marks
#Encoding = "cp437" #English problems
#Encoding = "cp500" #Western Europe
PYTHONUTF8=1 #Put Python in UTF-8 mode, good for WSL and windows operations https://docs.python.org/3/using/windows.html#utf-8-mode

prompt_fname = "raw_prompt.txt" #default. #copy prompt body to this file, which will be used for meld.
inputToken_safety_margin = 0.9 #This is a buffer factor between how many tokens the model can possibly take in and how many we feed into it. 
#This may be able to go higher. 
#TODO Make the maximum number of input tokens a commandline parameter
outputToken_safety_margin = 1.3 #This is a buffer factor between the maximum chunk input tokens and the minimum allowed output token limit. 
#This may need to go higher

#Argparse 
#argparse documentation: https://docs.python.org/3/library/argparse.html
parser = argparse.ArgumentParser(description='''A basic command line parser for GPT3-edit mode''', epilog = '''Command-line interface written by Anthony Barker, 2022. The main strucutre was written primarily by Shreya Shankar, Bora Uyumazturk, Devin Stein, Gulan, and Michael Lavelle''', prog="gpt_command_prompt")
parser.add_argument("prompt_inst", nargs='?', help="Instruction prompt string. If both this and -i files are give, this goes after the file contents.")
parser.add_argument("prompt_body", nargs='?', help="Body prompt string. If both this and -f files are give, this goes after the file contents.") #broken

parser.add_argument("-f","--files", help="Prompt file of body text to be edited.") #"files" for historical reasons but there's at most 1 file.
parser.add_argument("-i", dest="instruction_files", nargs='+', help="Prompt files, to be used for edit instructions.") 
parser.add_argument("-o", dest="out", help="Responce output file", default = "gptoutput.txt")  

parser.add_argument('-e', '--edit', action='store_true', help='Uses the text-davinci-edit-001 model, which is older but oriented around text editing')
parser.add_argument('-c', '--code', action='store_true', help='Uses the code-davinci-002 model to optomize code quality, and uses merged instruction and body and double the max input tokens. If combined with -e, uses code-davinci-edit-001.')
parser.add_argument('--old', nargs='?', const=1, type=int, help='Use older models with merged instructions and prompt for speed and cost. OLD: {no_arg = 1:text-davinci-003; 2:text-davinci-002; 3:Curie; 4: Babbage; 5+: Ada} ', default = 0)

#parser.add_argument('--old', action='store_true', help='Use GTP-3 (text-davinci-003 / code-davinci-002) with merged instructions and prompt. Can be combined with the -c/--code flag.')
parser.add_argument('-16k','--16k', dest="gpt_3point5_turbo_16k", action='store_true', help='Use gpt-3.5-turbo-16k, with 4x the context window of the default gpt-3.5-turbo. This flag overrides -c/--code, -e/--edit, and --old')
parser.add_argument('-n',"--max_tokens_in", type=int, help="Maximum word count (really token count) of each input prompt chunk. Default is 90%% of the model's limit") 
parser.add_argument("--max_tokens_out", type=int, help="Maximum word count (really token count) of responce, in order to prevent runaway output. Default is 20,000.") 
#The point here is to make sure chatGPT doesn't runaway. But this is really dumb since it's most likely to produce unwanted truncation. 
parser.add_argument("--top_p", type=float, help="top_p parameter. Controls diversity via nucleus sampling. 0.5 means half of all likelihood-weighted options are considered. Clamped to [0,1]", default = 1.0) 
parser.add_argument("--temp", type=float, help="temperature parameter. Controls randomness. Lowering results in less random completions. As the temperature approaches zero, the model will become deterministic and repetitive. Clamped to [0,1]", default = 0) 
parser.add_argument("-q", dest="frequency_penalty", type=float, help="frequency_penalty parameter. How much to penalize new tokens based on their existing frequency in the text so far. Decreases the model's likelihood of repeating the same line verbatim. Clamped to [0,2]", default = 0)
parser.add_argument("-p", dest="presence_penalty", type=float, help="presence_penalty parameter. How much to penalize new tokens based on whether they appear in the text so far. Increaces the model's likelihood to talk about new topics. Clamped to [0,2]", default = 0)

parser.add_argument('--echo', action='store_true', help='Print Prompt as well as responce')
parser.add_argument('--verbose', action='store_true', help='Spew everything')
parser.add_argument('-d', '--disable', action='store_true', help='Does not send command to GPT-3, used for prompt design and development')
parser.add_argument("-v", "--version", action='version', version='%(prog)s 0.3.0') 

#best of parameter, an int.
args = parser.parse_args() 

def clamp(num, minval,maxval):
	return max(min(num, maxval),minval)

def parse_fname(fname): #parse file names, returning the mantissa, and .extension
    i_dot = fname.rfind('.')
    return fname[:i_dot], fname[i_dot:]

#Model parameter prototypes: 
Instruction = ""
Prompt = ""
Top_p= clamp(args.top_p ,0.0,1.0) #1.0
Temp = clamp(args.temp ,0.0,1.0) #0
Frequency_penalty = clamp(args.frequency_penalty ,0.0,2.0) #0
Presence_penalty = clamp(args.presence_penalty ,0.0,2.0) #0

######### Input Ingestion ##############
if args.old == None:
    args.old = 1
    print("This should never run. Go fix args.old")

#Set Model
#Model = "gpt-3.5-turbo"
Model = "gpt-3.5-turbo-0613" #note, in terms of API compatability, here you can drop-in gpt-4, gpt-4-0613, gpt-4-32k, gpt-4-32k-0613, gpt-3.5-turbo, gpt-3.5-turbo-0613, gpt-3.5-turbo-16k, gpt-3.5-turbo-16k-0613
maxInputTokens  = 4096 #max tokens that the model can handle, or max that you're willing to supply, probably can go to 4096
use_chatGPT = True
price_in = 0.0015 #$/1000 tokens see https://openai.com/pricing
price_out = 0.002 #$/1000 tokens
if args.gpt_3point5_turbo_16k:
    Model = "gpt-3.5-turbo-16k" 
    maxInputTokens = 16000 #may be 16384. the webpage only says "16k". 
    use_chatGPT = True
    if args.old > 0 or args.code or args.edit: #if args.old or args.code or args.edit:
        print("Note that the --16k flag cannot be combined with -c/--code, -e/--edit, or --old, and the latter will be ignored.")
    price_in = 0.003 #$/1000 tokens
    price_out = 0.004 #$/1000 tokens
elif args.code and args.edit:
    Model = "code-davinci-edit-001"
    maxInputTokens = 3000 #4097 #pure guess. Might be 2049
    use_chatGPT = False
    price_in = 0.02 #$/1000 tokens see https://openai.com/pricing 
    print("Note: This is a relatively expensive model to run at 2 cents/1000 tokens in and out. ChatGPT is 10x cheaper")
    price_out = price_in 
elif args.code:
    Model = "code-davinci-002"
    maxInputTokens = 8001 #https://platform.openai.com/docs/models/gpt-3-5
    use_chatGPT = False
    price_in = 0.02 #$/1000 tokens see https://openai.com/pricing 
    print("Note: This is a relatively expensive model to run at 2 cents/1000 tokens in and out. ChatGPT is 10x cheaper")
    price_out = price_in 
elif args.edit:
    Model = "text-davinci-edit-001"
    maxInputTokens = 3000 #pure guess. Might be 2049
    use_chatGPT = False
    price_in = 0.02 #$/1000 tokens see https://openai.com/pricing 
    price_out = price_in 
elif args.old > 0: #elif args.old:
    #note, in terms of API compatability, here you can drop-in text-davinci-003, text-davinci-002, text-curie-001, text-babbage-001, text-ada-001
    if args.old == 1: #G
        Model = "text-davinci-003" #Best quality, longer output, and better consistent instruction-following than these other old models.
        maxInputTokens = 4097 #https://platform.openai.com/docs/models/gpt-3-5
        price_in = 0.02 #$/1000 tokens see https://openai.com/pricing 
        print("Note: This is a relatively expensive model to run at 2 cents/1000 tokens in and out. ChatGPT is 10x cheaper")
    elif args.old == 2:
        Model = "text-davinci-002" #Similar capabilities to text-davinci-003 but trained with supervised fine-tuning instead of reinforcement learning
        maxInputTokens = 4097 #https://platform.openai.com/docs/models/gpt-3-5
        price_in = 0.02 #$/1000 tokens see https://openai.com/pricing 
        print("Note: This is a relatively expensive model to run at 2 cents/1000 tokens in and out. ChatGPT is 10x cheaper")
    elif args.old == 3: #CURIE Very capable, but faster and lower cost than Davinci.
        Model = "text-curie-001" 
        maxInputTokens = 2049 #https://platform.openai.com/docs/models/gpt-3-5
        price_in = 0.0020 #$/1000 tokens see https://openai.com/pricing 
    elif args.old == 4: #BABBAGE Capable of straightforward tasks, very fast, and lower cost.
        Model = "text-babbage-001" 
        maxInputTokens = 2049 #https://platform.openai.com/docs/models/gpt-3-5
        price_in = 0.0005 #$/1000 tokens see https://openai.com/pricing 
    elif args.old >= 5: #ADA: Capable of very simple tasks, usually the fastest model in the GPT-3 series, and lowest cost.
        Model = "text-ada-001"
        maxInputTokens = 2049 #https://platform.openai.com/docs/models/gpt-3-5
        price_in = 0.0004 #$/1000 tokens see https://openai.com/pricing 
    use_chatGPT = False
    price_out = price_in 
    if args.frequency_penalty or args.presence_penalty:
        print("Note that with --old, the presence_penalty or frequency_penalty option do nothing")

#Convert from price per 1000 tokens to price per token 
price_out /= 1000 
price_in  /= 1000

#Instruction Prompt
if args.instruction_files: 
    for fname in args.instruction_files:
        if not os.path.exists(fname):
            print("Error: instruction file not found ",fname)
            sys.exit()
        if Instruction == "":
            with open(fname, 'r', encoding=Encoding, errors='ignore') as fin:
                Instruction = fin.read()
        else: 
            with open(fname, 'r', encoding=Encoding, errors='ignore') as fin:
                Instruction += '\n' + fin.read() 
if args.prompt_inst:
    if Instruction == "":
        Instruction += '\n' + args.prompt_inst
    else:
        Instruction = args.prompt_inst
if Instruction == "":
    print("Instruction prompt is required, none was given. Exiting.")
    sys.exit()
len_Instruction__tokens = token_cut_light.nchars_to_ntokens_approx(len(Instruction) ) 

if len_Instruction__tokens > 0.8*maxInputTokens:
    print(f"Error: Instructions are too long ({len_Instruction__tokens } tokens, while the model's input token maximum is {maxInputTokens} for both instructions and prompt.")
    sys.exit()

#make a safety margin on the input tokens
maxInputTokens -= len_Instruction__tokens 
if args.max_tokens_in:
    maxInputTokens = min(maxInputTokens, max(args.max_tokens_in, 25))
else:
    maxInputTokens = int(inputToken_safety_margin * maxInputTokens )

backup_gtp_file = "gtpoutput_backup.txt" 

output_file_set = False
if args.out:
    output_file_set = True

if args.files: 
        if not os.path.exists(args.files):
            print("Error: prompt file not found ",args.files)
            sys.exit()
        if Prompt == "":
            with open(args.files, 'r', encoding=Encoding, errors='ignore') as fin:
                Prompt = fin.read() 
                #if that doesn't work, try with open(path, 'rb') as f:
        else: 
            with open(args.files, 'r', encoding=Encoding, errors='ignore') as fin:
                Prompt += '\n' + fin.read() 

        prefix, extension = parse_fname(args.files)
        if not args.out:
            args.out = prefix+"__gtpMeld"+extension 
        backup_gtp_file = prefix+"__gtpRaw"+extension 
        prompt_fname = prefix+"__prmoptRaw"+extension 
if args.prompt_body:
    if Prompt == "":
        Prompt += '\n' + args.prompt_body
    else:
        Prompt = args.prompt_body
if Prompt == "":
    print("Body prompt is required, none was given. Exiting.")
    sys.exit()

#Set maxOutputTokens, 
maxOutputTokens_default = 20000 #default output limit to prevent run-away
maxOutputTokens = maxOutputTokens_default #default output limit to prevent run-away
if args.max_tokens_out:
    print("Warning: max_tokens_out is set. Are you sure you want to do that? This doesn't help with anything known but can cause gaps in the output")

    maxOutputTokens = abs(args.max_tokens_out)
    if args.max_tokens_out < 0:
        print(f"Negative max_tokens_out feature is obsolte.")
    if maxOutputTokens < maxInputTokens*outputToken_safety_margin:
        print(f"Clipping max_tokens_out {args.max_tokens_out} to {maxInputTokens*outputToken_safety_margin} to prevent periodic truncations in the output.")
        maxOutputTokens = max(maxOutputTokens, maxInputTokens*outputToken_safety_margin)

def get_front_white_idx(text): #tested
    #ret int indx of front white space
    l=len(text)
    for i in range(l):
        if not text[i].isspace():
            return i
    return l

def humanize_seconds(sec):
    if sec < 2:
        return f"{sec:.3f}s"
    elif sec < 90:
        return f"{sec:.2f} sec"
    elif sec < 3600:
        return f"{sec/60:.2f} min"
    elif sec < 3600:
        return f"{sec/60:.1f} min"
    elif sec < 86400:
        return f"{sec/3600:.1f} hrs"
    elif sec < 2592000:
        return f"{sec/86400:.1f} days"
    elif sec < 31556736:
        return f"{sec/2635200:.1f} months"
    else:
        return f"{sec/31556736:.1f} years"
    
if args.verbose:
    print("Model: ",Model)
    print("max_tokens_in: ",maxInputTokens )
    print("max_tokens_out: ",maxOutputTokens )
    print("Top_p",Top_p)
    print("Temp",Temp)

def get_back_white_idx(text, char_strt=0): #tested
    #ret int indx of back white space, starting from char 
    l=len(text)
    L=l-char_strt
    if L==0:
        return l
    for i in range(1,L):
        if not text[-i].isspace():
            return l-i+1
    return char_strt

def rechunk(text, len_text, chunk_start, chunk_end): #TO_TEST
    #resets the end of the chunk to make the chunks end at sensipble places. 
    #note that the character at chunk_end is excluded from that chunk

    max_lookback = int((chunk_end - chunk_start)*0.2) #loop back over last 20%
    file_end_snap_proximity = 20  #risks exceeding max tokens.
    weight = -0.01 #encourage later items

    #snap to the end of file. This also guards against overflow
    if len_text - chunk_end < file_end_snap_proximity:
        return len_text 

    ranking = {}
    for i in range( max(chunk_start, chunk_end - max_lookback), chunk_end):
        weight_i = (chunk_end - i)*weight
        char_i = text[i]
        char_ip = text[i+1]
        char_im = text[i-1]
            
        if char_i == ' ':
            if char_im in [".","?","!"] and (char_ip.isupper() or char_ip.isspace()):
                #end of sentence
                ranking[i] = 4 + weight_i 
            elif char_im in [",",";",":"]:
                #end of clause
                ranking[i] = 3 + weight_i 
            else:
                #common space
                ranking[i] = 2 + weight_i 
        elif char_i == '-':
            ranking[i] = 0.5 + weight_i 
        elif char_i == '\t':
            ranking[i] = 3 + weight_i 
        elif char_i.isspace() and char_im == '}' and not char_ip in ['}','{']:
            ranking[i] = 5 + weight_i 
        elif char_i == '\n':
            ranking[i] = 6 + weight_i 
        else:
            ranking[i] = 1 + weight_i 

    chunk_end = max(ranking, key=ranking.get)
    return chunk_end

with open(prompt_fname,'w') as fp:
    fp.write(Prompt)    

len_prompt__char = len(Prompt)
len_prompt__tokens_est = token_cut_light.nchars_to_ntokens_approx(len_prompt__char)
n_chunk_est = ceil(len_prompt__tokens_est/maxInputTokens)
est_cost__USD = price_in*(len_Instruction__tokens  + len_prompt__tokens_est) + price_out*len_prompt__tokens_est
    
if args.verbose:
    print(f"length of prompt body {len_prompt__char} characters, est. {len_prompt__tokens_est} tokens") 
    print(f"Estimating this will be {n_chunk_est} chunks")
if args.verbose or est_cost__USD > 0.1:
    print(f"Estimated cost of this action: ${est_cost__USD:.2f}")
if est_cost__USD > 0.5:
    answer = input("Would you like to continue? (y/n): ")
    if not (answer.lower() == 'y' or answer.lower == 'yes'):
        print("Disabling OpenAI API calls")
        args.disable = True

#Main 
#def run_loop( in_file_name, out_file_name, gtp_instructions,  maxInputTokens = 4095):
with open(args.out,'w') as fout:
            if not args.disable:
                openai.api_key = os.getenv("OPENAI_API_KEY")
            
            chunk_start = 0
            i_chunk = 0
            expected_n_chunks = token_cut_light.count_chunks_approx(len_prompt__char, maxInputTokens )

            t_start0 = time.time()
            while chunk_start < len_prompt__char:
                t_start = time.time()
                chunk_end = chunk_start + token_cut_light.guess_token_truncate_cutint_safer(Prompt, maxInputTokens) 
                chunk_end = rechunk(Prompt,len_prompt__char, chunk_start, chunk_end)
                chunk_length__char = chunk_end - chunk_start
                chunk_length__tokens_est = token_cut_light.nchars_to_ntokens_approx(chunk_length__char )
                chunk = Prompt[chunk_start : chunk_end]
                frac_done = chunk_end/len_prompt__char
                if args.echo or args.verbose: 
                    if args.verbose:
                        print(f"i_chunk {i_chunk} of ~{n_chunk_est }, chunk start at char {chunk_start} ends at char {chunk_end} (diff: {chunk_length__char} chars, est {chunk_length__tokens_est } tokens). Total Prompt length: {len_prompt__char} characters, moving to {100*frac_done:.2f}% of completion") 
                    else:
                        print(f"Prompt Chunk {i_chunk} of ~{n_chunk_est }:")
                    print(chunk)
                if args.verbose:
                    print(f"{100*chunk_start/len_prompt__char:.2f}% completed. Processing i_chunk {i_chunk} of ~{n_chunk_est}...") 
                front_white_idx = get_front_white_idx(chunk)
                chunk_front_white_space = chunk[:front_white_idx ]
                chunk_end_white_space = chunk[get_back_white_idx(chunk,front_white_idx):]
                stripped_chunk = chunk.strip()
                
                ntokens_in = 0
                ntokens_out = 0
                #GPT-3 CALL 
                if args.disable:
                     altchunk_course = chunk
                else:
                    if use_chatGPT:
                        conversation = [{"role": "system", "content": Instruction}]
                        conversation.append({"role":"user", "content": chunk})
                        if args.max_tokens_out:
                            result = openai.ChatCompletion.create(
                                    model=Model, 
                                    messages=conversation,
                                    temperature=Temp,
                                    max_tokens=maxOutputTokens,
                                    top_p=Top_p,
                                    frequency_penalty=Frequency_penalty,
                                    presence_penalty=Presence_penalty
                                    )
                            altchunk_course = result.choices[0].message.content
                            ntokens_in = result.usage.prompt_tokens
                            ntokens_out = result.usage.completion_tokens
                            """altchunk_course = openai.ChatCompletion.create(
                                    model=Model,
                                    messages=[{"role": "user", "content": Instruction+"\n\n"+chunk}],
                                    temperature=Temp,
                                    max_tokens=maxOutputTokens,
                                    top_p=Top_p,
                                    frequency_penalty=Frequency_penalty,
                                    presence_penalty=Presence_penalty
                                    ).choices[0].message.content"""
                        else:
                            result = openai.ChatCompletion.create(
                                    model=Model, 
                                    messages=conversation,
                                    temperature=Temp,
                                    #max_tokens=maxOutputTokens,
                                    top_p=Top_p,
                                    frequency_penalty=Frequency_penalty,
                                    presence_penalty=Presence_penalty
                                    )
                            altchunk_course = result.choices[0].message.content
                            ntokens_in = result.usage.prompt_tokens
                            ntokens_out = result.usage.completion_tokens
                            """altchunk_course = openai.ChatCompletion.create(
                                    model=Model,
                                    messages=[{"role": "user", "content": Instruction+"\n\n"+chunk}],
                                    temperature=Temp,
                                    #max_tokens=maxOutputTokens,
                                    top_p=Top_p,
                                    frequency_penalty=Frequency_penalty,
                                    presence_penalty=Presence_penalty
                                    ).choices[0].message.content """
                    elif args.old == 1:
                        if args.max_tokens_out:
                            result = openai.Completion.create(
                                    model=Model,
                                    prompt=Instruction+"\n\n"+chunk,
                                    temperature=Temp,
                                    max_tokens=maxOutputTokens,
                                    top_p=Top_p,
                                    frequency_penalty=Frequency_penalty,
                                    presence_penalty=Presence_penalty
                                    ).choices[0].text
                            altchunk_course = result.choices[0].text
                            ntokens_in = result.usage.prompt_tokens
                            ntokens_out = result.usage.completion_tokens
                        else:
                            result = openai.Completion.create(
                                    model=Model,
                                    prompt=Instruction+"\n\n"+chunk,
                                    temperature=Temp,
                                    #max_tokens=maxOutputTokens,
                                    top_p=Top_p,
                                    frequency_penalty=Frequency_penalty,
                                    presence_penalty=Presence_penalty
                                    )
                            altchunk_course = result.choices[0].text
                            ntokens_in = result.usage.prompt_tokens
                            ntokens_out = result.usage.completion_tokens
                    else:
                        if args.max_tokens_out:
                            result = openai.Edit.create( 
                                    model=Model,
                                    input=chunk,
                                    instruction=Instruction,
                                    temperature=Temp,
                                    max_tokens=maxOutputTokens,
                                    top_p=Top_p)
                            altchunk_course = result.choices[0].text
                            ntokens_in = result.usage.prompt_tokens
                            ntokens_out = result.usage.completion_tokens
                        else:
                            result = openai.Edit.create(
                                    model=Model,
                                    input=chunk,
                                    instruction=Instruction,
                                    temperature=Temp,
                                    #max_tokens=maxOutputTokens,
                                    top_p=Top_p)
                            altchunk_course = result.choices[0].text
                            ntokens_in = result.usage.prompt_tokens
                            ntokens_out = result.usage.completion_tokens
                altchunk = chunk_front_white_space +altchunk_course.strip() + chunk_end_white_space 
                #altchunk = chunk_front_white_space +altchunk_course.strip() + chunk_end_white_space+"@@@" #degug
                if args.verbose:
                    altchunk += f"\nEND CHUNK {i_chunk}. Tokens in: {ntokens_in}, tokens out: {ntokens_out}.\n"
                if ntokens_in > 0:
                    prop = abs(ntokens_in-ntokens_out)/ntokens_in
                    if prop < 0.6:
                        print(f"Warning: short output. Looks like a truncation error on chunk {i_chunk}. Tokens in: {ntokens_in}, tokens out: {ntokens_out}.")
                    elif prop > 1.5:
                        print(f"Warning: weirdly long output on chunk {i_chunk}. Tokens in: {ntokens_in}, tokens out: {ntokens_out}.")

                fout.write(altchunk)

                chunk_start = chunk_end
                i_chunk += 1

                if i_chunk > expected_n_chunks*1.5: #loop timout, for debug
                        print("loop ran to chunk",i_chunk, ". That seems too long. Breaking loop.")
                        break

                if args.echo or args.verbose:
                    total_run_time_so_far = time.time() - t_start0
                    total_expected_run_time = total_run_time_so_far/frac_done 
                    completion_ETA = total_expected_run_time - total_run_time_so_far
                    print(f"That was prompt chunk {i_chunk}, it was observed to be {ntokens_in} tokens (apriori estimated was {chunk_length__tokens_est } tokens).\nResponse Chunk {i_chunk} (responce length {ntokens_out} tokens)")
                    suffix = f"Chunk process time {humanize_seconds(time.time() - t_start)}. Total run time: {humanize_seconds(total_run_time_so_far)} out of {humanize_seconds(total_expected_run_time)}. Expected finish in {humanize_seconds(completion_ETA)}\n" 

                    print(altchunk + suffix)

#body input is already copied to prompt_fname
os.system("cp "+args.out+" "+backup_gtp_file+" &")
#print("meld "+prompt_fname +" "+args.out+" &")
if mac_mode:
    os.system(f"open -a Meld {prompt_fname} {args.out} &")
elif os.path.exists(meld_exe_file_path):
    meld_exe_file_path_callable = meld_exe_file_path.replace(" ", "\ ")
    os.system(f"{meld_exe_file_path_callable} {prompt_fname} {args.out} &")
else:
    print(f"Meld not found at path {meld_exe_file_path}. Try vimdiff or diff manually")
"""    try:
        os.system("vimdiff --version")
        os.system("vimdiff " + prompt_fname +" "+args.out+" &")
    except:
        print("vimdiff not found, resorting to diff :-/ ")
        os.system("diff " + prompt_fname +" "+args.out+" &")
        """
print(f"vimdiff {prompt_fname} {args.out}")
print("If you have a meld alias setup:")
print(f"meld {prompt_fname} {args.out} &")

with open("ok",'w') as fs:
    if not output_file_set:
        fs.write("mv " + args.out + " " +  args.files + '\n' )
    fs.write("rm " + prompt_fname + '\n')
    fs.write("rm " + backup_gtp_file + '\n' )
    fs.write("rm reject\n")
    fs.write("rm ok\n")

with open("reject",'w') as fs:
    fs.write("rm " + prompt_fname + '\n')
    fs.write("rm " + args.out + '\n' )
    fs.write("rm " + backup_gtp_file + '\n')
    fs.write("rm ok\n")
    fs.write("rm reject\n")
if args.files: 
    if output_file_set:
        print(f"\nAfter meld/vimdiff, accept changes with \n$ sc ok\nwhich cleans temp files. Final result is {args.out}.")
    else:
        print(f"\nAfter meld/vimdiff, accept changes with \n$ sc ok\nwhich cleans temp files, and overwrites the input file {args.out} with the output {args.files}")
else:
    print(f"\nAfter meld/vimdiff, accept changes with \n$ sc ok\nwhich cleans temp files.")
print("or reject changes with $ sc reject")

##OTHER GPT3 Examples##
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

#gpt = GPT(engine="davinci", temperature=0.5, max_tokens_out=100)
#prompt = "Display the lowest salary from the Worker table."
#output = gpt.submit_request(prompt)
