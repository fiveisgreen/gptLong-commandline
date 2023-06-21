import os, sys
import json
import openai
import argparse
import token_cut_light
#from gpt import GPT
import time
import random
from enum import Flag,auto, IntEnum

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
#  -c, --code            Uses the code-davinci-edit-001. (code-davinci-002 is no longer offered)
                        max input tokens. If combined with -e, uses 
#  --old [OLD]           Use older models with merged instructions and prompt for speed and cost. OLD: {no_arg = 1:text-davinci-003;
                        2:text-davinci-002; 3:Curie; 4: Babbage; 5+: Ada}

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

prompt_fname = "raw_prompt.txt" #default. #copy of the full prompt body to this file, which will be used for meld.
inputToken_safety_margin = 0.9 #This is a buffer factor between how many tokens the model can possibly take in and how many we feed into it. 
#This may be able to go higher. 
outputToken_safety_margin = 1.3 #This is a buffer factor between the maximum chunk input tokens and the minimum allowed output token limit.  #This may need to go higher

#Argparse 
def setupArgparse():
    #argparse documentation: https://docs.python.org/3/library/argparse.html
    parser = argparse.ArgumentParser(description='''A basic command line parser for GPT3-edit mode''', epilog = '''Command-line interface written by Anthony Barker, 2022. The main strucutre was written primarily by Shreya Shankar, Bora Uyumazturk, Devin Stein, Gulan, and Michael Lavelle''', prog="gpt_command_prompt")
    parser.add_argument("prompt_inst", nargs='?', help="Instruction prompt string. If both this and -i files are give, this goes after the file contents.")
    parser.add_argument("prompt_body", nargs='?', help="Body prompt string. If both this and -f files are give, this goes after the file contents.") #broken

    parser.add_argument("-f","--files", help="Prompt file of body text to be edited.") #"files" for historical reasons but there's at most 1 file.
    parser.add_argument("-i", dest="instruction_files", nargs='+', help="Prompt files, to be used for edit instructions.") 
    parser.add_argument("-o", dest="out", help="Responce output file", default = "gptoutput.txt")  

    parser.add_argument('-e', '--edit', action='store_true', help='Uses the text-davinci-edit-001 model, which is older but oriented around text editing')
    parser.add_argument('-c', '--code', action='store_true', help='Uses the code-davinci-edit-001 model to optomize code quality. (code-davinci-002 is no longer offered).')
    parser.add_argument('--old', nargs='?', const=1, type=int, help='Use older models with merged instructions and prompt for speed and cost. OLD: {no_arg = 1:text-davinci-003; 2:text-davinci-002; 3:Curie; 4: Babbage; 5+: Ada} ', default = 0)
        #default is used if no -t option is given. if -t is given with no param, then use const
    parser.add_argument('-16k','--16k', dest="gpt_3point5_turbo_16k", action='store_true', help='Use gpt-3.5-turbo-16k, with 4x the context window of the default gpt-3.5-turbo. This flag overrides -c/--code, -e/--edit, and --old')
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
    parser.add_argument("-v", "--version", action='version', version='%(prog)s 0.4.0') 

    args = parser.parse_args() 
    return args

args = setupArgparse()

def clamp(num, minval,maxval):
	return max(min(num, maxval),minval)

def parse_fname(fname): #parse file names, returning the mantissa, and .extension
    i_dot = fname.rfind('.')
    return fname[:i_dot], fname[i_dot:]


#Model parameter prototypes: 
backup_gtp_file = "gtpoutput_backup.txt"

######### Input Ingestion ##############
if args.old == None:
    args.old = 1
    print("Warning! This should never run. Go fix args.old")

class Verb(IntEnum):
    notSet=-1
    silent=0
    birthDeathMarriage=1
    test=2
    normal=3
    curious=4
    debug=5
    hyperbarf=9
verbosity = args.verbose

is_test_mode = (args.test >= 0)
if is_test_mode and verbosity <= Verb.notSet:
    verbosity = Verb.test
if verbosity == Verb.notSet:
    verbosity = Verb.normal

#Verbosity guide: 
#0: silent
#1: birth, death, marriage
#2: test mode, what you need for prompt engineering.
#3: more normal
#
#8:


class Model_Type(Flag):
    CHAT = auto()
    GPT3 = auto()
    EDIT = auto()

def to_int(thing):
    if(thing==None):
        return 0
    else:
        return int(thing)

# define a retry decorator
def retry_with_exponential_backoff(
    func,
    initial_delay: float = 1, #seconds
    exponential_base: float = 1.4, #Increace wait by the factor exponential_base * (1 + jitteriness*rand(0,1)) on each retry. OpenAI example is 2.0
    jitteriness: float = 0.4, #set to 0 to turn off jitter. OpenAI example is 1.0
    max_retries: int = 20,
    errors: tuple = (openai.error.RateLimitError,),
):
    """
    Retry a function with exponential backoff, coppied out of the OpenAI cookbook.
    https://github.com/openai/openai-cookbook/blob/main/examples/How_to_handle_rate_limits.ipynb
    May be replaced by the tenacity or backoff libraries.
    """
    jitteriness = abs(jitteriness)

    def wrapper(*args, **kwargs):
        # Initialize variables
        num_retries = 0
        delay = initial_delay

        # Loop until a successful response or max_retries is hit or an exception is raised
        while True:
            try:
                return func(*args, **kwargs)

            # Retry on specified errors
            except errors as e:
                # Increment retries
                num_retries += 1

                # Check if max retries has been reached
                if num_retries > max_retries:
                    raise Exception(
                        f"Maximum number of retries ({max_retries}) exceeded."
                    )

                # Increment the delay
                delay *= exponential_base * (1.0 + jitteriness * random.random()) #delay[sec] = exponential_base * (1 .. 2)

                # Sleep for the delay
                time.sleep(delay)

            # Raise exceptions for any errors not specified
            except Exception as e:
                raise e
            if num_retries > max_retries+1:
                break

    return wrapper

class Model_Controler:
    def __init__(self):
        self.model_type = Model_Type.CHAT
        self.use_max_tokens_out = False
        self.maxInputTokens = 2000 #max tokens to feed into the model at once
        self.model_maxInputTokens = self.maxInputTokens #theoretical max the model can take before error
        self.maxOutputTokens = 20000
        self.Temp = 0
        self.Top_p = 1
        self.Frequency_penalty = 0
        self.Presence_penalty = 0
        self.price_in = 0 #price per input and system token in USD
        self.price_out = 0 #price per input token in USD
        self.chunk = ""
        self.Model = ""
        self.Instruction = ""
        self.len_Instruction__tokens = 0
        #self.conversation = None
    def Set_Prices(self,price_per_1000_input_tokens__USD, price_per_1000_output_tokens__USD):
        #see https://openai.com/pricing
        self.price_in =  price_per_1000_input_tokens__USD/1000
        self.price_out = price_per_1000_output_tokens__USD/1000
    def Set_Top_p(self,top_p):
        self.Top_p= clamp(args.top_p ,0.0,1.0) 
    def Set_Frequency_penalty(self,frequency_penalty):
        self.Frequency_penalty = clamp(frequency_penalty ,0.0,2.0)
    def Set_Presence_penalty(self,presence_penalty):
        self.Presence_penalty = clamp(presence_penalty ,0.0,2.0) 
    def Set_Temp(self,temp):
        self.Temp = clamp(temp ,0.0,1.0) 
    def Set_Instruction(self,Instruction): 
        self.Instructions = Instruction
        len_Instruction__tokens = token_cut_light.nchars_to_ntokens_approx(len(self.Instruction) ) 
        if len_Instruction__tokens > 0.8*self.model_maxInputTokens:
            print(f"Error: Instructions are too long ({len_Instruction__tokens} tokens, while the model's input token maximum is {model_maxInputTokens} for both instructions and prompt.")
            sys.exit()
        self.len_Instruction__tokens = len_Instruction__tokens
    def Set_maxInputTokens(self,user_advised_max_tokens_in__bool, user_advised_max_tokens_in__int, inputToken_safety_margin=0.9):
        #MC.Set_maxInputTokens(bool(args.max_tokens_in), int(args.max_tokens_in), inputToken_safety_margin)
        #make a safety margin on the input tokens
        maxInputTokens = self.model_maxInputTokens - self.len_Instruction__tokens 
        if user_advised_max_tokens_in__bool:
            maxInputTokens = min(maxInputTokens, max(user_advised_max_tokens_in__int, 25))
        else:
            maxInputTokens = int(inputToken_safety_margin * maxInputTokens )
        self.maxInputTokens = maxInputTokens
    def Set_maxOutputTokens(self,user_advised_max_tokens_out__bool,user_advised_max_tokens_out__int=0,outputToken_safety_margin=2.0, verbosity=Verb.normal):
        #Must come after Set_maxInputTokens. better to instead call Set_TokenMaximua
        maxOutputTokens_default = 20000 #default output limit to prevent run-away
        maxOutputTokens = maxOutputTokens_default #default output limit to prevent run-away
        if user_advised_max_tokens_out__bool:
            if verbosity > Verb.birthDeathMarriage:
                print("Warning: max_tokens_out is set. Are you sure you want to do that? This doesn't help with anything known but can cause gaps in the output") 
    
            maxOutputTokens = abs(user_advised_max_tokens_out__int)
            if args.max_tokens_out < 0 and verbosity > Verb.birthDeathMarriage:
                print(f"Negative max_tokens_out feature is obsolte.") 
            if maxOutputTokens < self.maxInputTokens*outputToken_safety_margin and verbosity > Verb.birthDeathMarriage:
                print(f"Clipping max_tokens_out {args.max_tokens_out} to {maxInputTokens*outputToken_safety_margin} to prevent periodic truncations in the output.") 
                maxOutputTokens = max(maxOutputTokens, self.maxInputTokens*outputToken_safety_margin)
        self.maxOutputTokens = maxOutputTokens
    def Set_TokenMaxima(self,user_advised_max_tokens_in__bool, user_advised_max_tokens_in__int, inputToken_safety_margin,user_advised_max_tokens_out__bool,user_advised_max_tokens_out__int,outputToken_safety_margin, verbosity=Verb.normal):
        self.Set_maxInputTokens(user_advised_max_tokens_in__bool, user_advised_max_tokens_in__int, inputToken_safety_margin)
        self.Set_maxOutputTokens(user_advised_max_tokens_out__bool,user_advised_max_tokens_out__int,outputToken_safety_margin, verbosity)
    def Set_Model(self,modelname, verbosity=Verb.normal):
        self.Model = modelname
        if self.Model == "gpt-3.5-turbo":
            self.model_type = Model_Type.CHAT
            self.model_maxInputTokens  = 4096 #max tokens that the model can handle
            self.Set_Prices(0.0015, 0.002) #(price_per_1000_input_tokens__USD, price_per_1000_output_tokens__USD)
        elif self.Model == "gpt-3.5-turbo-0613":
            self.model_type = Model_Type.CHAT
            self.model_maxInputTokens  = 4096 #max tokens that the model can handle
            self.Set_Prices(0.0015, 0.002) #(price_per_1000_input_tokens__USD, price_per_1000_output_tokens__USD)
        elif self.Model == "gpt-3.5-turbo-16k":
            self.model_type = Model_Type.CHAT
            self.model_maxInputTokens = 16000 #may be 16384. the webpage only says "16k". 
            self.Set_Prices(0.003, 0.004) #(price_per_1000_input_tokens__USD, price_per_1000_output_tokens__USD)
        elif self.Model == "code-davinci-edit-001":
            self.model_type = Model_Type.EDIT
            self.model_maxInputTokens = 3000 #4097 #pure guess. Might be 2049
            self.Set_Prices(0.02, 0.02) #(price_per_1000_input_tokens__USD, price_per_1000_output_tokens__USD)
            if verbosity > Verb.birthDeathMarriage:
                print("Note: This is a relatively expensive model to run at 2 cents/1000 tokens in and out. ChatGPT is 10x cheaper")
        elif self.Model == "text-davinci-edit-001":
            self.model_type = Model_Type.EDIT
            self.model_maxInputTokens = 3000 #pure guess. Might be 2049
            self.Set_Prices(0.02,0.02)
        elif self.Model == "text-davinci-003": #Best quality, longer output, and better consistent instruction-following than these other old models.
            self.model_type = Model_Type.GPT3
            self.model_maxInputTokens = 4097 #https://platform.openai.com/docs/models/gpt-3-5
            self.Set_Prices(0.02,0.02)
        elif self.Model == "text-davinci-002": #Similar capabilities to text-davinci-003 but trained with supervised fine-tuning instead of reinforcement learning
            self.model_type = Model_Type.GPT3
            self.model_maxInputTokens = 4097 #https://platform.openai.com/docs/models/gpt-3-5
            self.Set_Prices(0.02,0.02)
        elif self.Model == "text-curie-001":
            self.model_type = Model_Type.GPT3
            self.model_maxInputTokens = 2049 #https://platform.openai.com/docs/models/gpt-3-5
            self.Set_Prices(0.002,0.002)
        elif self.Model == "text-babbage-001":
            self.model_type = Model_Type.GPT3
            self.model_maxInputTokens = 2049 #https://platform.openai.com/docs/models/gpt-3-5
            self.Set_Prices(0.0005,0.0005)
            price_in = 0.0005 #$/1000 tokens see https://openai.com/pricing 
        elif self.Model == "text-ada-001":
            self.model_type = Model_Type.GPT3
            self.model_maxInputTokens = 2049 #https://platform.openai.com/docs/models/gpt-3-5
            self.Set_Prices(0.0004,0.0004)
        else:
            print(f"Error! model {self.Model} not defined in this program") #TODO make this less dumb
            sys.exit()
        self.maxInputTokens = self.model_maxInputTokens 
                    ###############
    @retry_with_exponential_backoff
    def Run_OpenAI_LLM__Instruct(self,prompt_body):
        #responce, ntokens_in, ntokens_out = MC.Run_OpenAI_LLM(model )
        responce = ""
        ntokens_in = 0
        ntokens_out = 0
        if self.model_type == Model_Type.CHAT:
            conversation = [{"role": "system", "content": self.Instruction}]
            conversation.append({"role":"user", "content": prompt_body})
            if self.use_max_tokens_out:
                result = openai.ChatCompletion.create(
                        model=self.Model, 
                        messages=conversation,
                        temperature= self.Temp,
                        max_tokens= self.maxOutputTokens,
                        top_p= self.Top_p,
                        frequency_penalty= self.Frequency_penalty,
                        presence_penalty= self.Presence_penalty
                        )
                responce = result.choices[0].message.content
                ntokens_in = result.usage.prompt_tokens
                ntokens_out = result.usage.completion_tokens
            else:
                result = openai.ChatCompletion.create(
                        model= self.Model, 
                        messages= conversation,
                        temperature= self.Temp,
                        #max_tokens= self.maxOutputTokens,
                        top_p= self.Top_p,
                        frequency_penalty= self.Frequency_penalty,
                        presence_penalty= self.Presence_penalty
                        )
                responce = result.choices[0].message.content
                ntokens_in = result.usage.prompt_tokens
                ntokens_out = result.usage.completion_tokens
        elif self.model_type == Model_Type.GPT3:
            if self.use_max_tokens_out:
                result = openai.Completion.create(
                        model= self.Model,
                        prompt= self.Instruction+"\n\n"+prompt_body,
                        temperature= self.Temp,
                        max_tokens= self.maxOutputTokens,
                        top_p= self.Top_p,
                        frequency_penalty= self.Frequency_penalty,
                        presence_penalty= self.Presence_penalty
                        ).choices[0].text
                responce = result.choices[0].text
                ntokens_in = result.usage.prompt_tokens
                ntokens_out = result.usage.completion_tokens
            else:
                result = openai.Completion.create(
                        model= self.Model,
                        prompt= self.Instruction+"\n\n"+prompt_body,
                        temperature= self.Temp,
                        #max_tokens= self.maxOutputTokens,
                        top_p= self.Top_p,
                        frequency_penalty= self.Frequency_penalty,
                        presence_penalty= self.Presence_penalty
                        )
                responce = result.choices[0].text
                ntokens_in = result.usage.prompt_tokens
                ntokens_out = result.usage.completion_tokens
        elif self.model_type == Model_Type.EDIT:
                if self.use_max_tokens_out:
                    result = openai.Edit.create( 
                            model= self.Model,
                            input= prompt_body,
                            instruction= self.Instruction,
                            temperature= self.Temp,
                            max_tokens= self.maxOutputTokens,
                            top_p= self.Top_p)
                    responce = result.choices[0].text
                    ntokens_in = result.usage.prompt_tokens
                    ntokens_out = result.usage.completion_tokens
                else:
                    result = self. openai.Edit.create(
                            model= self.Model,
                            input= prompt_body,
                            instruction= self.Instruction,
                            temperature= self.Temp,
                            #max_tokens= self.maxOutputTokens,
                            top_p= self.Top_p)
                    responce = self. result.choices[0].text
                    ntokens_in = self. result.usage.prompt_tokens
                    ntokens_out = self. result.usage.completion_tokens
        else:
            print("Error: invalid model_type")
            sys.exit()
        return responce, ntokens_in, ntokens_out
                    ###############
    def Get_PriceEstimate(self, len_prompt__tokens_est):
        est_cost__USD = self.price_in*(self.len_Instruction__tokens  + len_prompt__tokens_est) + self.price_out*len_prompt__tokens_est 
        return est_cost__USD


MC = Model_Controler()
MC.Set_Top_p(args.top_p)
MC.Set_Frequency_penalty(args.frequency_penalty)
MC.Set_Presence_penalty(args.presence_penalty)
MC.Set_Temp(args.temp)

#################################################
#Set Model
def SetModelFromArgparse(args, MC, verbosity=Verb.normal):
    #MC = SetModel(args, MC)
    #MC.Set_Model("gpt-3.5-turbo")
    MC.Set_Model("gpt-3.5-turbo-0613")
    if args.gpt_3point5_turbo_16k:
        MC.Set_Model("gpt-3.5-turbo-16k")
        if verbosity > Verb.birthDeathMarriage and (args.old > 0 or args.code or args.edit): #if args.old or args.code or args.edit:
            print("Note that the --16k flag cannot be combined with -c/--code, -e/--edit, or --old, and the latter will be ignored.")
    elif args.code:
        MC.Set_Model("code-davinci-edit-001")
        if verbosity > Verb.birthDeathMarriage:
            print("Note: This is a relatively expensive model to run at 2 cents/1000 tokens in and out. ChatGPT is 10x cheaper")
    elif args.edit:
        MC.Set_Model("text-davinci-edit-001")
    elif args.old > 0: #elif args.old:
        #note, in terms of API compatability, here you can drop-in text-davinci-003, text-davinci-002, text-curie-001, text-babbage-001, text-ada-001
        if args.old == 1: #Best quality, longer output, and better consistent instruction-following than these other old models
            MC.Set_Model("text-davinci-003")
            if verbosity > Verb.birthDeathMarriage:
                print("Note: This is a relatively expensive model to run at 2 cents/1000 tokens in and out. ChatGPT is 10x cheaper")
        elif args.old == 2:#Similar capabilities to text-davinci-003 but trained with supervised fine-tuning instead of reinforcement learning
            MC.Set_Model("text-davinci-002") 
            if verbosity > Verb.birthDeathMarriage:
                print("Note: This is a relatively expensive model to run at 2 cents/1000 tokens in and out. ChatGPT is 10x cheaper")
        elif args.old == 3: #CURIE Very capable, but faster and lower cost than Davinci.
            MC.Set_Model("text-curie-001" )
        elif args.old == 4: #BABBAGE Capable of straightforward tasks, very fast, and lower cost.
            MC.Set_Model("text-babbage-001" )
        elif args.old >= 5: #ADA: Capable of very simple tasks, usually the fastest model in the GPT-3 series, and lowest cost.
            MC.Set_Model("text-ada-001")
        if verbosity > Verb.birthDeathMarriage and (args.frequency_penalty or args.presence_penalty):
            print("Note that with --old, the presence_penalty or frequency_penalty option do nothing")
    return MC
MC = SetModelFromArgparse(args, MC, verbosity)
#Model, model_maxInputTokens, is_chatGPT,price_in, price_out = SetModel(args)

#Instruction Prompt
def GetInstructionPrompt(args):
    #Instruction = GetInstructionPrompt(args)
    Instruction = ""
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
        print("Error: Instruction prompt is required, none was given. Exiting.")
        sys.exit()
    return Instruction
MC.Set_Instruction(GetInstructionPrompt(args))
#MC.Set_maxInputTokens(bool(args.max_tokens_in), int(args.max_tokens_in), inputToken_safety_margin)
#MC.Set_maxOutputTokens(bool(args.max_tokens_out),int(args.max_tokens_out),outputToken_safety_margin) #must come after 
MC.Set_TokenMaxima(bool(args.max_tokens_in), to_int(args.max_tokens_in), inputToken_safety_margin,
                   bool(args.max_tokens_out),to_int(args.max_tokens_out),outputToken_safety_margin,
                   verbosity)

output_file_set = bool(args.out)

def GetBodyPrompt(args):
    Prompt = ""
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
        print("Error: Body prompt is required, none was given. Exiting.")
        sys.exit()
    return Prompt
Prompt = GetBodyPrompt(args)

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

def DoFileDiff(args,mac_mode,meld_exe_file_path,prompt_fname, backup_gtp_file, verbosity):
    #body input is already copied to prompt_fname
    os.system("cp "+args.out+" "+backup_gtp_file+" &")
    
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
    if verbosity > Verb.birthDeathMarriage:
        print(f"vimdiff {prompt_fname} {args.out}")
        print("If you have a meld alias setup:")
        print(f"meld {prompt_fname} {args.out} &")
DoFileDiff(args,mac_mode,meld_exe_file_path,prompt_fname, backup_gtp_file, verbosity)

def MakeOkRejectFiles(out_file, prompt_files,output_file_set,prompt_fname,backup_gtp_file, verbosity, is_test_mode):
    ok_file = "ok"
    reject_file = "reject"
    with open(ok_file,'w') as fs:
        if not output_file_set and not is_test_mode:
            fs.write(f"mv {out_file} {prompt_files}\n" ) #bug? what's up here?
        fs.write(f"rm {prompt_fname}\n") #the backup copy of the complete prompt
        fs.write(f"rm {backup_gtp_file}\n")
        fs.write(f"rm {reject_file}\n")
        fs.write(f"rm {ok_file}\n")
    
    with open(reject_file,'w') as fs:
        fs.write(f"rm {prompt_fname}\n")
        fs.write(f"rm {out_file}\n" )
        fs.write(f"rm {backup_gtp_file}\n")
        fs.write(f"rm {ok_file}\n")
        fs.write(f"rm {reject_file}\n")

    if verbosity > Verb.birthDeathMarriage:
        if args.files: 
            if output_file_set:
                print(f"\nAfter meld/vimdiff, accept changes with \n$ sc {ok_file}\nwhich cleans temp files. Final result is {args.out}.")
            else:
                print(f"\nAfter meld/vimdiff, accept changes with \n$ sc {ok_file}\nwhich cleans temp files, and overwrites the input file {args.out} with the output {args.files}")
        else:
            print(f"\nAfter meld/vimdiff, accept changes with \n$ sc {ok_file}\nwhich cleans temp files.")
        print("or reject changes with $ sc {reject_file}")
MakeOkRejectFiles(args.out, args.files, output_file_set, prompt_fname,backup_gtp_file, verbosity, is_test_mode)
