import os, sys
import openai
import argparse
import time
from typing import Tuple
import token_cut_light as tcl
from gpt_utils import *

#example: 
#gpt "my prompt" [epilog prompt] [-n max length]
#gpt -f file1 file2

#TODO: 
#- [x] get rid of the GPT library... what's it even for?  Clear out all the junk from the fork
#- [ ] enable example file
#- [x] make a sensible integration of chatGPT into the command system
#- [ ] integrate conversation into the chatGPT option
#- [ ] integrate older models since they have much higher token rate limits.
#- [ ] check that max tokens isn't 
#- [ ] make use of maxInputTokens to prevent crashes from exceeding the token limit

#todo: make a conversation system -- finally, a use for standrd io
#automated conversatoin mode

"""SETTINGS"""
version_number__str = "0.3.0"

inputToken_safety_margin = 0.9 #This is a buffer factor between how many tokens the model can possibly take in and how many we feed into it. 
#This may be able to go higher. 
outputToken_safety_margin = 1.3 #This is a buffer factor between the maximum chunk input tokens and the minimum allowed output token limit.  #This may need to go higher

#Argparse 
def setupArgparse():
    #argparse documentation: https://docs.python.org/3/library/argparse.html
    parser = argparse.ArgumentParser(description='''A basic command line parser for GPT3''', epilog = '''Command-line interface written by Anthony Barker, 2022. The main strucutre was written primarily by Shreya Shankar, Bora Uyumazturk, Devin Stein, Gulan, and Michael Lavelle''',prog="gpt_command_prompt")
    
    parser.add_argument("bodyPrompt_cmdLnStr", nargs='?', help="Body prompt string. If both this and -f files are give, this goes after the file contents.") #broken #TODO fix this
    parser.add_argument("bodyPrompt_epilog_cmdLnStr", nargs='?', help="Epilog prompt string") #broken

    parser.add_argument("-f","--file", nargs='+', help="Prompt file, will not be used for tokens counts") 
    parser.add_argument('-ln',"--lines", nargs=2, type=int, help="Line number range to consider for body text files. -l [line_from line_to]. Negative numbers go to beginning, end respectively. Line numbers start at 1", default=[-1, -1])

    parser.add_argument("-o", dest="out", help="Responce output file", default = "gptoutput.txt")  


    parser.add_argument('-c', '--code', action='store_true', help='Uses the code-davinci-edit-001 model to optomize code quality. (code-davinci-002 is no longer offered).') #TODO does this still work??
    parser.add_argument('-g4', '--gpt4', action='store_true', help='Uses a GPT-4 model. Usually this is gpt-4, but if combined with -l, gpt-4-32k will be used.')
    parser.add_argument('--old', nargs='?', const=1, type=int, help='Use older models with merged instructions and prompt for speed and cost. OLD: {no_arg = 1:text-davinci-003; 2:text-davinci-002; 3:Curie; 4: Babbage; 5+: Ada} ', default = 0)
    parser.add_argument('-l','--long', dest="long_context", action='store_true', help='Use gpt-3.5-turbo-16k, with 4x the context window of the default gpt-3.5-turbo. This flag overrides -c/--code and --old')
    parser.add_argument('-n',"--max_tokens_in", type=int, help="Maximum word count (really token count) of each input prompt chunk. Default is 90%% of the model's limit") 
    parser.add_argument("--max_tokens_out", type=int, help="Maximum word count (really token count) of responce, in order to prevent runaway output. Default is 20,000.") 
    #The point here is to make sure chatGPT doesn't runaway. But this is really dumb since it's most likely to produce unwanted truncation. 
    parser.add_argument("--top_p", type=float, help="top_p parameter. Controls diversity via nucleus sampling. 0.5 means half of all likelihood-weighted options are considered. Clamped to [0,1]", default = 1.0) 
    parser.add_argument("--temp", type=float, help="temperature parameter. Controls randomness. Lowering results in less random completions. As the temperature approaches zero, the model will become deterministic and repetitive. Clamped to [0,1]", default = 0) 
    parser.add_argument("-q", dest="frequency_penalty", type=float, help="frequency_penalty parameter. How much to penalize new tokens based on their existing frequency in the text so far. Decreases the model's likelihood of repeating the same line verbatim. Clamped to [0,2]", default = 0)
    parser.add_argument("-p", dest="presence_penalty", type=float, help="presence_penalty parameter. How much to penalize new tokens based on whether they appear in the text so far. Increaces the model's likelihood to talk about new topics. Clamped to [0,2]", default = 0)

    parser.add_argument('--echo', action='store_true', help='Print Prompt as well as responce')
    parser.add_argument('--verbose', nargs='?', const=3, type=int, help='How verbose to print. 0 = silent.',default = -1)
    parser.add_argument('-d', '--disable', action='store_true', help='Does not send command to GPT-3, used for prompt design and development')
    parser.add_argument("-v", "--version", action='version', version=f'%(prog)s {version_number__str}') 

    args = parser.parse_args() 
    return args

def SetModelFromArgparse(args, MC):
    #uses args.gpt4: args.old args.code args.frequency_penalty args.presence_penalty

    MC.Set_Model("gpt-3.5-turbo")
    #MC.Set_Model("gpt-3.5-turbo-0613")
    if args.long_context:
        if args.gpt4:
            MC.Set_Model("gpt-4-32k")
        else:
            MC.Set_Model("gpt-3.5-turbo-16k")
        if MC.verbosity > Verb.birthDeathMarriage and (args.old > 0 or args.code): #if args.old or args.code or args.edit:
            print("Note that the -l/--long flag cannot be combined with -c/--code or --old, and the latter will be ignored.")
    elif args.gpt4:
        MC.Set_Model("gpt-4")
    elif args.code:
        MC.Set_Model("code-davinci-edit-001")
#    elif args.edit:
#        MC.Set_Model("text-davinci-edit-001")
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

PC = Process_Controler()
PC.Set_disable_openAI_calls(args.disable)
PC.Set_Files(output_file_is_set = bool(args.out),\
            output_filename = args.out,\
            bodyPrompt_file_is_set = bool(args.file),\
            bodyPrompt_filename = args.file) #TODO

MC = Model_Controler()
MC.Set_Verbosity(args.verbose, PC.is_test_mode ) #TODO what to do about echo?
    #verbose |= args.echo or args.disable or args.verbose
MC.Set_Top_p(args.top_p)
MC.Set_Frequency_penalty(args.frequency_penalty)
MC.Set_Presence_penalty(args.presence_penalty)
MC.Set_Temp(args.temp)
MC = SetModelFromArgparse(args, MC)
MC.Set_TokenMaxima(bool(args.max_tokens_in), to_int(args.max_tokens_in), inputToken_safety_margin,
                   bool(args.max_tokens_out),to_int(args.max_tokens_out),outputToken_safety_margin)

Prompt = GetPromptMultipleFiles(\
            bool(args.bodyPrompt_cmdLnStr),   args.bodyPrompt_cmdLnStr,\
            bool(args.file), args.file, \
            bool(args.bodyPrompt_epilog_cmdLnStr),   args.bodyPrompt_epilog_cmdLnStr, "body")\
        )

len_prompt__char = len(Prompt)
length_is_ok, length_is_ok_theoreticlly, len_prompt__tokens_est = MC.Prompt_Length_Is_Ok(len_prompt__char)

if not length_is_ok_theoreticlly:
    sys.exit()

if MC.verbosity >= Verb.debug:
    MC.Print()
    print(f"length of prompt body {len_prompt__char} characters, est. {len_prompt__tokens_est} tokens") 

#Cost estimate dialogue
MC.Discuss_Pricing_with_User(len_prompt__char)

if PC.echo or PC.verbosity >= Verb.hyperbarf:
    print("Prompt: ")
    print(Prompt)

response, ntokens_in, ntokens_out = MC.Run_OpenAI_LLM(Prompt)
    
if args.out: 
   with open(args.out,'w') as fout:
       fout.write(response)
    
PC.OpenOutputInTextEditor()

##OTHER GPT3 Examples##
#gpt = GPT(engine="davinci", temperature=0.5, max_tokens=maxOutputTokens)

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

