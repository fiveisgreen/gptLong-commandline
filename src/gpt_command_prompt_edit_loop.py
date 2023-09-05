import os, sys
import openai
import argparse
import token_cut_light
#from gpt import GPT
import time

from gpt_utils import *

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
    - [ ] Refactor to make the guts of this a function. 
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
prompt_fname = "raw_prompt.txt" #default. #copy of the full prompt body to this file, which will be used for meld.
inputToken_safety_margin = 0.9 #This is a buffer factor between how many tokens the model can possibly take in and how many we feed into it. 
#This may be able to go higher. 
outputToken_safety_margin = 1.3 #This is a buffer factor between the maximum chunk input tokens and the minimum allowed output token limit.  #This may need to go higher

#Argparse 
#maybe replace with setupArgparse_gpte()
def setupArgparse():
    #argparse documentation: https://docs.python.org/3/library/argparse.html
    parser = argparse.ArgumentParser(description='''A basic command line parser for GPT3-edit mode''', epilog = '''Command-line interface written by Anthony Barker, 2022. The main strucutre was written primarily by Shreya Shankar, Bora Uyumazturk, Devin Stein, Gulan, and Michael Lavelle''', prog="gpt_command_prompt")
    parser.add_argument("prompt_inst", nargs='?', help="Instruction prompt string. If both this and -i files are give, this goes after the file contents.") 
    parser.add_argument("prompt_body", nargs='?', help="Body prompt string. If both this and -f files are give, this goes after the file contents.") #broken #TODO fix this

    parser.add_argument("-f","--files", help="Prompt file of body text to be edited.") #"files" for historical reasons but there's at most 1 file.
    #parser.add_argument("-f","--files", nargs='+',help="Prompt file of body text to be edited.") #"files" for historical reasons but there's at most 1 file. #TODO Make this go
    parser.add_argument('-ln',"--lines", nargs=2, type=int, help="Line number range to consider for body text files. -l [line_from line_to]. Negative numbers go to beginning, end respectively. Line numbers start at 1", default=[-1, -1])
    parser.add_argument("-i", dest="instruction_files", nargs='+', help="Prompt files, to be used for edit instructions.") 
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
    parser.add_argument("-v", "--version", action='version', version='%(prog)s 0.5.0') 

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

args = setupArgparse()

#Model parameter prototypes: 
backup_gtp_file = "gtpoutput_backup.txt"

######### Input Ingestion ##############
if args.old == None:
    args.old = 1
    print("Warning! This should never run. Go fix args.old")

is_test_mode = (args.test >= 0)

MC = Model_Controler()
MC.Set_Verbosity(args.verbose, is_test_mode )
MC.Set_Top_p(args.top_p)
MC.Set_Frequency_penalty(args.frequency_penalty)
MC.Set_Presence_penalty(args.presence_penalty)
MC.Set_Temp(args.temp)

MC = SetModelFromArgparse(args, MC)

MC.Set_Instruction(GetInstructionPrompt(args.instruction_files, args.prompt_inst))
MC.Set_TokenMaxima(bool(args.max_tokens_in), to_int(args.max_tokens_in), inputToken_safety_margin,
                   bool(args.max_tokens_out),to_int(args.max_tokens_out),outputToken_safety_margin)


output_file_set = bool(args.out)

Prompt = GetBodyPrompt(args.files, args.lines, args.prompt_body)

prefix, extension = parse_fname(fname)
if not args.out: 
    args.out = prefix+"__gtpMeld"+extension 
backup_gtp_file = prefix+"__gtpRaw"+extension 
prompt_fname = prefix+"__prmoptRaw"+extension 

with open(prompt_fname,'w') as fp:
    fp.write(Prompt)    

len_prompt__char = len(Prompt)
len_prompt__tokens_est = token_cut_light.nchars_to_ntokens_approx(len_prompt__char)
est_cost__USD = MC.Get_PriceEstimate(len_prompt__tokens_est)
expected_n_chunks = token_cut_light.count_chunks_approx(len_prompt__char, MC.maxInputTokens )
    
#if args.verbose: #TODO make this a class member
if verbosity >= Verb.normal:
    print("Model: ",MC.Model)
    print("max_tokens_in: ",MC.maxInputTokens )
    print("max_tokens_out: ",MC.maxOutputTokens )
    print("Top_p",MC.Top_p)
    print("Temp",MC.Temp)
    print(f"length of prompt body {len_prompt__char} characters, est. {len_prompt__tokens_est} tokens") 
    print(f"Estimating this will be {expected_n_chunks} chunks")

#Cost estimate dialogue
if verbosity >= Verb.normal or est_cost__USD > 0.1:
    print(f"Estimated cost of this action: ${est_cost__USD:.2f}")
    if est_cost__USD > 0.5 and verbosity != Verb.silent:
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
            t_start0 = time.time()
            while chunk_start < len_prompt__char:

                if is_test_mode: 
                    if i_chunk >= args.test:
                        break

                t_start = time.time()

                    #chunk_end, frac_done = func(chunk_start, Prompt, MC.maxInputTokens, len_prompt__char)
                chunk_end = chunk_start + token_cut_light.guess_token_truncate_cutint_safer(Prompt[chunk_start:], MC.maxInputTokens)
                chunk_end = rechunk(Prompt,len_prompt__char, chunk_start, chunk_end)
                chunk_length__char = chunk_end - chunk_start
                chunk_length__tokens_est = token_cut_light.nchars_to_ntokens_approx(chunk_length__char )
                chunk = Prompt[chunk_start : chunk_end]
                frac_done = chunk_end/len_prompt__char
                if verbosity >= Verb.normal:
                    print(f"i_chunk {i_chunk} of ~{expected_n_chunks }, chunk start at char {chunk_start} ends at char {chunk_end} (diff: {chunk_length__char} chars, est {chunk_length__tokens_est } tokens). Total Prompt length: {len_prompt__char} characters, moving to {100*frac_done:.2f}% of completion") 
                if args.echo or verbosity >= Verb.hyperbarf:
                    print(f"Prompt Chunk {i_chunk} of ~{expected_n_chunks }:")
                    print(chunk)
                if verbosity >= Verb.normal:
                    print(f"{100*chunk_start/len_prompt__char:.2f}% completed. Processing i_chunk {i_chunk} of ~{expected_n_chunks}...") 
                chunk_start = chunk_end

                front_white_idx = get_front_white_idx(chunk)
                chunk_front_white_space = chunk[:front_white_idx ]
                chunk_end_white_space = chunk[get_back_white_idx(chunk,front_white_idx):]
                stripped_chunk = chunk.strip()
                
                ntokens_in = 0
                ntokens_out = 0
                if args.disable:
                     altchunk_course = chunk
                else:
                    #GPT-3 CALL 
                    altchunk_course, ntokens_in, ntokens_out = MC.Run_OpenAI_LLM__Instruct(chunk)

                altchunk = chunk_front_white_space +altchunk_course.strip() + chunk_end_white_space 

                if is_test_mode and i_chunk >= args.test -1:
                    altchunk += "\n Output terminated by test option"
                    if verbosity > Verb.silent:
                        print("\n Output terminated by test option")

                if verbosity >= Verb.debug: 
                    altchunk += f"\nEND CHUNK {i_chunk}. Tokens in: {ntokens_in}, tokens out: {ntokens_out}.\n"
                if ntokens_in > 0 and verbosity != Verb.silent:
                    prop = abs(ntokens_in-ntokens_out)/ntokens_in
                    if prop < 0.6:
                        print(f"Warning: short output. Looks like a truncation error on chunk {i_chunk}. Tokens in: {ntokens_in}, tokens out: {ntokens_out}.")
                    elif prop > 1.5:
                        print(f"Warning: weirdly long output on chunk {i_chunk}. Tokens in: {ntokens_in}, tokens out: {ntokens_out}.")

                fout.write(altchunk)

                i_chunk += 1

                if i_chunk > expected_n_chunks*1.5: #loop timout, for debug
                        if verbosity != Verb.silent:
                            print("Error: Loop ran to chunk",i_chunk, ". That seems too long. Breaking loop.")
                        break

                total_run_time_so_far = time.time() - t_start0
                total_expected_run_time = total_run_time_so_far/frac_done 
                completion_ETA = total_expected_run_time - total_run_time_so_far
                suffix = f"Chunk process time {humanize_seconds(time.time() - t_start)}. Total run time: {humanize_seconds(total_run_time_so_far)} out of {humanize_seconds(total_expected_run_time)}. Expected finish in {humanize_seconds(completion_ETA)}\n" 
                if verbosity >= Verb.normal:
                    print(f"That was prompt chunk {i_chunk}, it was observed to be {ntokens_in} tokens (apriori estimated was {chunk_length__tokens_est } tokens).\nResponse Chunk {i_chunk} (responce length {ntokens_out} tokens)")
                if args.echo or verbosity >= Verb.hyperbarf:
                    print(altchunk + suffix)
                if is_test_mode and i_chunk >= args.test -1 and verbosity > Verb.silent:
                    print("\n Output terminated by test option")

DoFileDiff(args.out,mac_mode,meld_exe_file_path,prompt_fname, backup_gtp_file, MC.verbosity)

MakeOkRejectFiles(args.out, args.files, output_file_set, prompt_fname, backup_gtp_file, MC.verbosity, is_test_mode)
