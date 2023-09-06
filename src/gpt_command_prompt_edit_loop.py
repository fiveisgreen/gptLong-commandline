import os, sys
import openai
import argparse
import time
from typing import Tuple
import token_cut_light as tcl
from gpt_utils import *

""" #################### USAGE AND EXAMPLES ###########################

###### Examples ######

$ gtpe "my instruction prompt" -f body_file [-o outfile]
$ gpte "my instruction prompt" "my body prompt to edit" 
$ gtpe -f body_file1 -i instr_file1 instr_file2 [-o outfile]

####### FUll Usage #######
$ gtpe ["instructions"] ["body epilog"] [-f body.txt] [-i instruction1.txt instrcution2.txt] [-o outfile.txt] [params] [flags]


positional arguments:
  instPrompt_cmdLnStr           Instruction prompt string. If both this and -i files are give, this goes after the file contents.
  bodyPrompt_cmdLnStr           Body prompt string. If both this and -f files are give, this goes after the file contents.

IO:
#   Just supply a text string and it becomes appended to the front of the instruction prompt 
#  -i INSTRUCTION_FILES [INSTRUCTION_FILES ...]
                        Prompt files, to be used for edit instructions.
#  -f FILES, --files FILES
                        Prompt file of body text to be edited.
#  -o OUT                Responce output file

Model Selectors:
#  -l, --long           Use a model with a longer context window. By default this is gpt-3.5-turbo-16k, with 4x the context window of the default gpt-3.5-turbo. If combined with --gpt4, gpt-4-32k will be used. This flag overrides -c/--code, -e/--edit, and --old
#  -e, --edit            Uses the text-davinci-edit-001 model, which is older but oriented around text editing
#  -c, --code            Uses the code-davinci-edit-001. (code-davinci-002 is no longer offered)
                        max input tokens. If combined with -e, uses 
#  --old [OLD]           Use older models with merged instructions and prompt for speed and cost. OLD: {no_arg = 1:text-davinci-003;
                        2:text-davinci-002; 3:Curie; 4: Babbage; 5+: Ada}
#  -g4, --gpt4          Use GPT-4. If combined with --long uses GPT-4-32k

Flags:
#  -h, --help   show all options and exit
# -e --edit     switch engine to an edit oriented model
# -c --code     switch engine to code mode
# --old         switch engine from edit mode to merged prompt mode with instruction prolog.
# --echo     prints prompt and responce to terminal
# --verbose [verbosity] How verbose to print
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
    - [x] Refactor to make verbose into verbosity, an int from 0 .. 9
    - [x] Refactor into classes and functions
    - [ ] Migrate these improvements to the gpt command
    - [x] Refactor to make the guts of this a function. 
    - [x] Add time estimate
    - [x] make old integer parameterizable, and able to run ada, babage etc.
    - [x] Add price estimate and warnings
    - [x] Add rate limiter so you don't get rate errors. 
        Overview: https://platform.openai.com/docs/guides/rate-limits/overview
        cookbook: https://github.com/openai/openai-cookbook/blob/main/examples/How_to_handle_rate_limits.ipynb
        avoidance script: https://github.com/openai/openai-cookbook/blob/main/examples/api_request_parallel_processor.py
    - [x?] (Not needed?) Encode the rate limits for each model, preferably in some extneral file. 
    - [ ] Add parallel processing of chunks, 
        see https://github.com/openai/openai-cookbook/blob/main/examples/api_request_parallel_processor.py
        see https://github.com/openai/openai-cookbook/blob/90ef0f25e5615fa2bdd5982d6ce1162f4e3839c6/examples/api_request_parallel_processor.py
        #async def create_chat_completion():
        #    chat_completion_resp = await openai.ChatCompletion.acreate(model="gpt-3.5-turbo", messages=[{"role": "user", "content": "Hello world"}])

    - [x] add chunk limiter to test output. Maybe just a "test" mode
    - [x] Gracefully check that all filex exist before doing anything else.
    - [ ] Make a compare tool to compare the output of different models
    - [x] Make GPT-4 ready.
    - [x] Make it take in line numbers for -f files
    - [ ] Make it take an arbitrary number of body files, sequentially operating on each file in edit mode. 
    - [ ] Make a doc string tool -- maybe an insert mode -- maybe something seperate.
"""


"""SETTINGS"""
version_number__str = "0.6.0"

inputToken_safety_margin = 0.9 #This is a buffer factor between how many tokens the model can possibly take in and how many we feed into it. 
#This may be able to go higher. 
outputToken_safety_margin = 1.3 #This is a buffer factor between the maximum chunk input tokens and the minimum allowed output token limit.  #This may need to go higher

#Argparse 
#maybe replace with setupArgparse_gpte()
def setupArgparse():
    #argparse documentation: https://docs.python.org/3/library/argparse.html
    parser = argparse.ArgumentParser(description='''A basic command line parser for GPT3-edit mode''', epilog = '''Command-line interface written by Anthony Barker, 2022. The main strucutre was written primarily by Shreya Shankar, Bora Uyumazturk, Devin Stein, Gulan, and Michael Lavelle''', prog="gpt_command_prompt")
    parser.add_argument("instPrompt_cmdLnStr", nargs='?', help="Instruction prompt string. If both this and -i files are give, this goes after the file contents.") 
    parser.add_argument("bodyPrompt_cmdLnStr", nargs='?', help="Body prompt string. If both this and -f files are give, this goes after the file contents.") #broken #TODO fix this

    parser.add_argument("-f","--file", help="Prompt file of body text to be edited.") #"files" for historical reasons but there's at most 1 file.
    #parser.add_argument("-f","--files", nargs='+',help="Prompt file of body text to be edited.") #"files" for historical reasons but there's at most 1 file. #TODO Make this go
    parser.add_argument('-ln',"--lines", nargs=2, type=int, help="Line number range to consider for body text files. -l [line_from line_to]. Negative numbers go to beginning, end respectively. Line numbers start at 1", default=[-1, -1])
    parser.add_argument("-i", dest="instruction_filenames", nargs='+', help="Prompt files, to be used for edit instructions.") 
    parser.add_argument("-o", dest="out", help="Responce output file", default = "gptoutput.txt")  

    parser.add_argument('-e', '--edit', action='store_true', help='Uses the text-davinci-edit-001 model, which is older but oriented around text editing')
    parser.add_argument('-c', '--code', action='store_true', help='Uses the code-davinci-edit-001 model to optomize code quality. (code-davinci-002 is no longer offered).')
    parser.add_argument('-g4', '--gpt4', action='store_true', help='Uses a GPT-4 model. Usually this is gpt-4, but if combined with -l, gpt-4-32k will be used.')
    parser.add_argument('--old', nargs='?', const=1, type=int, help='Use older models with merged instructions and prompt for speed and cost. OLD: {no_arg = 1:text-davinci-003; 2:text-davinci-002; 3:Curie; 4: Babbage; 5+: Ada} ', default = 0)
        #default is used if no -t option is given. if -t is given with no param, then use const
    parser.add_argument('-l','--long', dest="long_context", action='store_true', help='Use gpt-3.5-turbo-16k, with 4x the context window of the default gpt-3.5-turbo. This flag overrides -c/--code, -e/--edit, and --old')
    #parser.add_argument('-16k','--16k', dest="gpt_3point5_turbo_16k", action='store_true', help='Use gpt-3.5-turbo-16k, with 4x the context window of the default gpt-3.5-turbo. This flag overrides -c/--code, -e/--edit, and --old')
    parser.add_argument('-n',"--max_tokens_in", type=int, help="Maximum word count (really token count) of each input prompt chunk. Default is 90%% of the model's limit") 
    parser.add_argument("--max_tokens_out", type=int, help="Maximum word count (really token count) of responce, in order to prevent runaway output. Default is 20,000.") 
    #The point here is to make sure chatGPT doesn't runaway. But this is really dumb since it's most likely to produce unwanted truncation. 
    parser.add_argument("--top_p", type=float, help="top_p parameter. Controls diversity via nucleus sampling. 0.5 means half of all likelihood-weighted options are considered. Clamped to [0,1]", default = 1.0) 
    parser.add_argument("--temp", type=float, help="temperature parameter. Controls randomness. Lowering results in less random completions. As the temperature approaches zero, the model will become deterministic and repetitive. Clamped to [0,1]", default = 0) 
    parser.add_argument("-q", dest="frequency_penalty", type=float, help="frequency_penalty parameter. How much to penalize new tokens based on their existing frequency in the text so far. Decreases the model's likelihood of repeating the same line verbatim. Clamped to [0,2]", default = 0)
    parser.add_argument("-p", dest="presence_penalty", type=float, help="presence_penalty parameter. How much to penalize new tokens based on whether they appear in the text so far. Increaces the model's likelihood to talk about new topics. Clamped to [0,2]", default = 0)

    parser.add_argument('--echo', action='store_true', help='Print Prompt as well as responce')
    parser.add_argument('--verbose', nargs='?', const=3, type=int, help='How verbose to print. 0 = silent.',default = -1)
    parser.add_argument('-t',"--test", nargs='?', const=2, type=int, help='Put the system in test mode for prompt engineering, which runs a limited number of chunks that can be set here (default is 2). It also turns on some extra printing', default = -1)
        #default is used if no -t option is given. if -t is given with no param, then use const
    parser.add_argument('-d', '--disable', action='store_true', help='Does not send command to GPT-3, used for prompt design and development')
    parser.add_argument("-v", "--version", action='version', version=f'%(prog)s {version_number__str}') 

    args = parser.parse_args() 
    return args

def SetModelFromArgparse(args, MC):
    #uses args.gpt4: args.old args.code args.edit args.frequency_penalty args.presence_penalty

    #MC.Set_Model("gpt-3.5-turbo")
    MC.Set_Model("gpt-3.5-turbo-0613")
    if args.long_context:
        if args.gpt4:
            MC.Set_Model("gpt-4-32k")
        else:
            MC.Set_Model("gpt-3.5-turbo-16k")
        if MC.verbosity > Verb.birthDeathMarriage and (args.old > 0 or args.code or args.edit): #if args.old or args.code or args.edit:
            print("Note that the -l/--long flag cannot be combined with -c/--code, -e/--edit, or --old, and the latter will be ignored.")
    elif args.gpt4:
        MC.Set_Model("gpt-4")
    elif args.code:
        MC.Set_Model("code-davinci-edit-001")
    elif args.edit:
        MC.Set_Model("text-davinci-edit-001")
    elif args.old > 0:
        #These all have the same API compatability
        old_models = {1:"text-davinci-003",2:"text-davinci-002", 3:"text-curie-001",4:"text-babbage-001", 5:"text-ada-001"}
        old_model_index = min(5,args.old)
        MC.Set_Model(old_models[old_model_index])
        if MC.verbosity > Verb.birthDeathMarriage and (args.frequency_penalty or args.presence_penalty):
            print("Note that with --old, the presence_penalty or frequency_penalty option do nothing")
    return MC

######### Input Ingestion ##############
args = setupArgparse()
if args.old == None:
    args.old = 1
    print("Warning! This should never run. Go fix args.old")
    assert False

PC = Process_Controler()
PC.Set_Test_Chunks(args.test)
PC.Set_disable_openAI_calls(args.disable)
PC.Set_Files(output_file_is_set = bool(args.out),\
            output_filename = args.out,\
            bodyPrompt_file_is_set = bool(args.file),\
            bodyPrompt_filename = args.file)

MC = Model_Controler()
MC.Set_Verbosity(args.verbose, PC.is_test_mode )
MC.Set_Top_p(args.top_p)
MC.Set_Frequency_penalty(args.frequency_penalty)
MC.Set_Presence_penalty(args.presence_penalty)
MC.Set_Temp(args.temp)
MC = SetModelFromArgparse(args, MC)
MC.Set_Instruction(\
    GetPromptMultipleFiles(\
            bool(args.instruction_filenames), args.instruction_filenames, \
            bool(args.instPrompt_cmdLnStr),   args.instPrompt_cmdLnStr, "instruction")\
        )
MC.Set_TokenMaxima(bool(args.max_tokens_in), to_int(args.max_tokens_in), inputToken_safety_margin,
                   bool(args.max_tokens_out),to_int(args.max_tokens_out),outputToken_safety_margin)

Prologue, Prompt, Epilogue = \
            GetPromptSingleFile(PC.bodyPrompt_file_is_set, PC.bodyPrompt_filename, \
            bool(args.bodyPrompt_cmdLnStr), args.bodyPrompt_cmdLnStr, "body",  args.lines)

with open(PC.backup_bodyPrompt_filename,'w') as fp:
    fp.write(Prologue)
    fp.write(Prompt)    
    fp.write(Epilogue)

len_prompt__char = len(Prompt)
len_prompt__tokens_est = tcl.nchars_to_ntokens_approx(len_prompt__char)
est_cost__USD = MC.Get_PriceEstimate(len_prompt__tokens_est)
    
#if args.verbose: #TODO make this a class member
if PC.verbosity >= Verb.normal:
    print("Model: ",MC.Model)
    print("max_tokens_in: ",MC.maxInputTokens )
    print("max_tokens_out: ",MC.maxOutputTokens )
    if PC.verbosity > Verb.normal:
        print("Top_p",MC.Top_p)
        print("Temp",MC.Temp)
    print(f"length of prompt body {len_prompt__char} characters, est. {len_prompt__tokens_est} tokens") 
    print(f"Estimating this will be {tcl.count_chunks_approx(len_prompt__char, MC.maxInputTokens )} chunks")

#Cost estimate dialogue
if PC.verbosity >= Verb.normal or est_cost__USD > 0.1:
    print(f"Estimated cost of this action: ${est_cost__USD:.2f}")
    if est_cost__USD > 0.5 and PC.verbosity != Verb.silent:
        answer = input("Would you like to continue? (y/n): ")
        if not (answer.lower() == 'y' or answer.lower == 'yes'):
            print("Disabling OpenAI API calls")
            PC.Set_disable_openAI_calls(True)

#Main Loop and LLM calls:
Loop_LLM_to_file(Prompt, len_prompt__char, MC, PC, Prologue, Epilogue)

PC.DoFileDiff()
PC.MakeOkRejectFiles()
