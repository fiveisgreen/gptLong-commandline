import os, sys
import openai
import token_cut_light as tcl
import time
import random
from typing import Tuple, List, Union
from enum import Flag, auto, IntEnum

"""SETTINGS"""
meld_exe_file_path = "/mnt/c/Program Files/Meld/MeldConsole.exe" #don't use backslashes before spaces. Don't worry about this if you're on mac.
notepad_exe_file_path = "/mnt/c/windows/system32/notepad.exe"

#list of all encoding options https://docs.python.org/3/library/codecs.html#standard-encodings
Encoding = "utf8" #
#Encoding = "latin1" #ok regardless of utf8 mode, but tends to wrech singla and double quotation marks
#Encoding = "cp437" #English problems
#Encoding = "cp500" #Western Europe
PYTHONUTF8=1 #Put Python in UTF-8 mode, good for WSL and windows operations https://docs.python.org/3/using/windows.html#utf-8-mode

"""
def setupArgparse_gpte():
    #argparse documentation: https://docs.python.org/3/library/argparse.html
    parser = argparse.ArgumentParser(description='''A basic command line parser for GPT3-edit mode''', epilog = '''Command-line interface written by Anthony Barker, 2022. The main strucutre was written primarily by Shreya Shankar, Bora Uyumazturk, Devin Stein, Gulan, and Michael Lavelle''', prog="gpt_command_prompt")
    parser.add_argument("prompt_inst", nargs='?', help="Instruction prompt string. If both this and -i files are give, this goes after the file contents.") 
    parser.add_argument("prompt_body", nargs='?', help="Body prompt string. If both this and -f files are give, this goes after the file contents.") #broken #TODO fix this
    parser.add_argument("-f","--files", help="File of body prompt text to be edited.") #"files" for historical reasons but there's at most 1 file.
    #parser.add_argument("-f","--files", nargs='+',help="Prompt file of body text to be edited.") #"files" for historical reasons but there's at most 1 file. #TODO Make this go
    parser.add_argument('-ln',"--lines", nargs=2, type=int, help="Line number range to consider for body text files. -l [line_from line_to]. Negative numbers go to beginning, end respectively. Line numbers start at 1", default=[-1, -1])
    parser.add_argument("-i", dest="instruction_files", nargs='+', help="Instruction prompt files, to be used for edit instructions.") 
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
    parser.add_argument('--echo', action='store_true', help='Print prompt as well as responce')
    parser.add_argument('--verbose', nargs='?', const=3, type=int, help='How verbose to print. 0 = silent.',default = -1)
    parser.add_argument('-t',"--test", nargs='?', const=2, type=int, help='Put the system in test mode for prompt engineering, which runs a limited number of chunks that can be set here (default is 2). It also turns on some extra printing', default = -1)
        #default is used if no -t option is given. if -t is given with no param, then use const
    parser.add_argument('-d', '--disable', action='store_true', help='Does not send command to GPT-3, used for prompt design and development')
    parser.add_argument("-v", "--version", action='version', version='%(prog)s 0.5.0') 
    args = parser.parse_args() 
    return args
"""

def clamp(num, minval, maxval):
	return max(min(num, maxval),minval)

def parse_fname(fname:str) -> Tuple[str,str]: #parse file names, returning the mantissa, and .extension
    i_dot = fname.rfind('.')
    return fname[:i_dot], fname[i_dot:]

class Verb(IntEnum):
    notSet=-1
    silent=0
    birthDeathMarriage=1
    test=2
    normal=3
    curious=4
    debug=5
    hyperbarf=9

class Model_Type(Flag):
    CHAT = auto()
    GPT3 = auto()
    EDIT = auto()

def to_int(thing) -> int:
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
        self.disable_openAI_calls:bool = False
        self.model_type = Model_Type.CHAT
        self.use_max_tokens_out = False
        self.is_instruct_mode = False
        self.maxInputTokens = 2000 #max tokens to feed into the model at once
        self.model_maxInputTokens = self.maxInputTokens #theoretical max the model can take before error
        self.maxOutputTokens = 20000
        self.Temp = 0
        self.Top_p = 1
        self.Frequency_penalty = 0
        self.Presence_penalty = 0
        self.price_in = 0 #price per input and system token in USD
        self.price_out = 0 #price per input token in USD
        #self.chunk = ""
        self.Model = ""
        self.Instruction = ""
        self.len_Instruction__tokens = 0
        self.verbosity=Verb.normal
        #self.conversation = None
    def Prompt_Length_Is_Ok(self, len_prompt__char:int) -> Tuple[bool,bool,int]:
        #returns bools tokens_within_policy_limit, tokens_within_theoretical_limit, estimated_ntokens_in_prompt
        len_prompt__tokens_est = tcl.nchars_to_ntokens_approx(len_prompt__char)
            #the token counter is an estimate, so we may make a policy to have the threshold lower than the model maximum
            #if the length is under this limit, then length_is_ok_by_policy = true
        length_is_ok_by_policy = len_prompt__tokens_est < self.maxInputTokens
            #we may also want to know if our policy is to stringent. So also report whether we are under the model limit. 
            #This signal may be WRONG if the token estimate isn't very good and we may actually be over the limit
        length_is_ok_theoreticlly = len_prompt__tokens_est<model_maxInputTokens
        if self.verbosity != Verb.silent and not length_is_ok_by_policy:
            if length_is_ok_theoreticlly:
                print(f"Warning! This prompt length has {len_prompt__tokens_est} estimated tokens exceeds the policy limit of {self.maxInputTokens} tokens. It may or may not exceed {self.Model}'s token limit of {self.model_maxInputTokens} tokens.")
            else:
                print(f"Error! This prompt length has {len_prompt__tokens_est} estimated tokens exceeds {self.Model}'s token limit of {self.model_maxInputTokens} tokens.")
        return length_is_ok_by_policy, length_is_ok_theoreticlly, len_prompt__tokens_est

    def Set_disable_openAI_calls(self,disable:bool) -> None:
        self.disable_openAI_calls = disable
    def Discuss_Pricing_with_User(self, len_prompt__char:int) -> None:
        len_prompt__tokens_est = tcl.nchars_to_ntokens_approx(len_prompt__char)
        est_cost__USD = self.Get_PriceEstimate(len_prompt__tokens_est)
        if self.verbosity >= Verb.normal or (est_cost__USD > 0.1 and self.verbosity != Verb.silent):
            print(f"Estimated cost of this action: ${est_cost__USD:.2f}")
            if est_cost__USD > 0.5 and self.verbosity != Verb.silent:
                answer = input("Would you like to continue? (y/n): ")
                if not (answer.lower() == 'y' or answer.lower == 'yes'):
                    print("Disabling OpenAI API calls")
                    self.Set_disable_openAI_calls(True)
    def Set_Verbosity(self,verbosity:Verb,is_test_mode = False ) -> None:
        if is_test_mode and verbosity <= Verb.notSet:
            self.verbosity = Verb.test
        elif verbosity == Verb.notSet:
            self.verbosity = Verb.normal
        else:
            self.verbosity = verbosity
    def Set_Prices(self,price_per_1000_input_tokens__USD:float, price_per_1000_output_tokens__USD:float) -> None:
        #see https://openai.com/pricing
        self.price_in =  price_per_1000_input_tokens__USD/1000
        self.price_out = price_per_1000_output_tokens__USD/1000
    def Set_Top_p(self,top_p:float) -> None:
        self.Top_p= clamp(top_p ,0.0,1.0) 
    def Set_Frequency_penalty(self,frequency_penalty:float) -> None:
        self.Frequency_penalty = clamp(frequency_penalty ,0.0,2.0)
    def Set_Presence_penalty(self,presence_penalty:float) -> None:
        self.Presence_penalty = clamp(presence_penalty ,0.0,2.0) 
    def Set_Temp(self,temp:float) -> None:
        self.Temp = clamp(temp ,0.0,1.0) 
    def Set_Instruction(self,Instruction:str) -> None: 
        self.is_instruct_mode = is_instruct_mode
        self.Instructions = Instruction
        len_Instruction__tokens = tcl.nchars_to_ntokens_approx(len(self.Instruction) ) 
        if len_Instruction__tokens > 0.8*self.model_maxInputTokens:
            print(f"Error: Instructions are too long ({len_Instruction__tokens} tokens, while the model's input token maximum is {model_maxInputTokens} for both instructions and prompt.")
            sys.exit()
        self.len_Instruction__tokens = len_Instruction__tokens
    def Set_maxInputTokens(self,there_is_user_advised_max_tokens_in:bool, user_advised_max_tokens_in:int, inputToken_safety_margin:float=0.9) -> None:
        #MC.Set_maxInputTokens(bool(args.max_tokens_in), int(args.max_tokens_in), inputToken_safety_margin)
        #make a safety margin on the input tokens
        maxInputTokens = self.model_maxInputTokens - self.len_Instruction__tokens 
        if there_is_user_advised_max_tokens_in:
            maxInputTokens = min(maxInputTokens, max(user_advised_max_tokens_in, 25))
        else:
            maxInputTokens = int(inputToken_safety_margin * maxInputTokens )
        self.maxInputTokens = maxInputTokens
    def Print(self):
      print("Model: ",self.Model)
      print("max_tokens_in: ",self.maxInputTokens )
      print("max_tokens_out: ",self.maxOutputTokens )
      if PC.verbosity > Verb.normal:
          print("Top_p",self.Top_p)
          print("Temp",self.Temp)
    def Set_maxOutputTokens(self,there_is_user_advised_max_tokens_out:bool,user_advised_max_tokens_out:int=0,outputToken_safety_margin:float=2.0) -> None:
        #Must come after Set_maxInputTokens. better to instead call Set_TokenMaximua
        maxOutputTokens_default = 20000 #default output limit to prevent run-away
        maxOutputTokens = maxOutputTokens_default #default output limit to prevent run-away
        if there_is_user_advised_max_tokens_out:
            if self.verbosity > Verb.birthDeathMarriage:
                print("Warning: max_tokens_out is set. Are you sure you want to do that? This doesn't help with anything known but can cause gaps in the output") 
    
            maxOutputTokens = abs(user_advised_max_tokens_out)
            if args.max_tokens_out < 0 and self.verbosity > Verb.birthDeathMarriage:
                print(f"Negative max_tokens_out feature is obsolte.") 
            if maxOutputTokens < self.maxInputTokens*outputToken_safety_margin and self.verbosity > Verb.birthDeathMarriage:
                print(f"Clipping max_tokens_out {args.max_tokens_out} to {maxInputTokens*outputToken_safety_margin} to prevent periodic truncations in the output.") 
                maxOutputTokens = max(maxOutputTokens, self.maxInputTokens*outputToken_safety_margin)
        self.maxOutputTokens = maxOutputTokens
    def Set_TokenMaxima(self,there_is_user_advised_max_tokens_in:bool, user_advised_max_tokens_in:int, inputToken_safety_margin:float,
            there_is_user_advised_max_tokens_out:bool,user_advised_max_tokens_out:int,outputToken_safety_margin:float) -> None:
        self.Set_maxInputTokens(there_is_user_advised_max_tokens_in, user_advised_max_tokens_in, inputToken_safety_margin)
        self.Set_maxOutputTokens(there_is_user_advised_max_tokens_out,user_advised_max_tokens_out,outputToken_safety_margin)
    def Set_Model(self,modelname:str) -> None:
        self.Model = modelname
        if self.Model == "gpt-3.5-turbo":
            self.model_type = Model_Type.CHAT
            self.model_maxInputTokens  = 4096 #max tokens that the model can handle
            self.Set_Prices(0.0015, 0.002) #(price_per_1000_input_tokens__USD, price_per_1000_output_tokens__USD)
        elif self.Model == "gpt-3.5-turbo-0613":
            self.model_type = Model_Type.CHAT
            self.model_maxInputTokens  = 4096 #max tokens that the model can handle
            self.Set_Prices(0.0015, 0.002) #(price_per_1000_input_tokens__USD, price_per_1000_output_tokens__USD)
        elif self.Model == "gpt-4":
            self.model_type = Model_Type.CHAT
            self.model_maxInputTokens = 8192 
            self.Set_Prices(0.03, 0.06) #(price_per_1000_input_tokens__USD, price_per_1000_output_tokens__USD)
        elif self.Model == "gpt-4-32k":
            self.model_type = Model_Type.CHAT
            self.model_maxInputTokens = 32768 
            self.Set_Prices(0.06, 0.12) #(price_per_1000_input_tokens__USD, price_per_1000_output_tokens__USD)
        elif self.Model == "gpt-3.5-turbo-16k":
            self.model_type = Model_Type.CHAT
            self.model_maxInputTokens = 16384 
            self.Set_Prices(0.003, 0.004) #(price_per_1000_input_tokens__USD, price_per_1000_output_tokens__USD)
        elif self.Model == "code-davinci-edit-001":
            self.model_type = Model_Type.EDIT
            self.model_maxInputTokens = 3000 #4097 #pure guess. Might be 2049
            self.Set_Prices(0.02, 0.02) #(price_per_1000_input_tokens__USD, price_per_1000_output_tokens__USD)
            if self.verbosity > Verb.birthDeathMarriage:
                print("Note: This is a relatively expensive model to run at 2 cents/1000 tokens in and out. ChatGPT is 10x cheaper")
        elif self.Model == "text-davinci-edit-001":
            self.model_type = Model_Type.EDIT
            self.model_maxInputTokens = 3000 #pure guess. Might be 2049
            self.Set_Prices(0.02,0.02)
        elif self.Model == "text-davinci-003": #Best quality, longer output, and better consistent instruction-following than these other old models.
            self.model_type = Model_Type.GPT3
            self.model_maxInputTokens = 4097 #https://platform.openai.com/docs/models/gpt-3-5
            self.Set_Prices(0.02,0.02)
            if self.verbosity > Verb.birthDeathMarriage:
                print("Note: This is a relatively expensive model to run at 2 cents/1000 tokens in and out. ChatGPT is 10x cheaper")
        elif self.Model == "text-davinci-002": #Similar capabilities to text-davinci-003 but trained with supervised fine-tuning instead of reinforcement learning
            self.model_type = Model_Type.GPT3
            self.model_maxInputTokens = 4097 #https://platform.openai.com/docs/models/gpt-3-5
            self.Set_Prices(0.02,0.02)
            if self.verbosity > Verb.birthDeathMarriage:
                print("Note: This is a relatively expensive model to run at 2 cents/1000 tokens in and out. ChatGPT is 10x cheaper")
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
    def Run_OpenAI_LLM(self,prompt_body:str) -> Tuple[str, int, int]:
        #responce, ntokens_in, ntokens_out = MC.Run_OpenAI_LLM(body_prompt)
        responce = ""
        ntokens_in = 0
        ntokens_out = 0
        if self.model_type == Model_Type.CHAT:
            conversation = []
            if self.is_instruct_mode:
                conversation = [{"role": "system", "content": self.Instruction}]
                conversation.append({"role":"user", "content": prompt_body})
            else:
                conversation =[{"role":"user", "content": prompt_body}]
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
            Prompt = ""
            if self.is_instruct_mode:
                Prompt= self.Instruction+"\n\n"+prompt_body
            else:
                Prompt= prompt_body

            if self.use_max_tokens_out:
                result = openai.Completion.create(
                        model= self.Model,
                        prompt= Prompt,
                        temperature= self.Temp,
                        max_tokens= self.maxOutputTokens,
                        top_p= self.Top_p,
                        frequency_penalty= self.Frequency_penalty,
                        presence_penalty= self.Presence_penalty
                        )
                responce = result.choices[0].text
                ntokens_in = result.usage.prompt_tokens
                ntokens_out = result.usage.completion_tokens
            else:
                result = openai.Completion.create(
                        model= self.Model,
                        prompt= Prompt,
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
                            instruction= self.Instruction, #if not is_instruct_mode, should be ""
                            temperature= self.Temp,
                            max_tokens= self.maxOutputTokens,
                            top_p= self.Top_p)
                    responce = result.choices[0].text
                    ntokens_in = result.usage.prompt_tokens
                    ntokens_out = result.usage.completion_tokens
                else:
                    result = self.openai.Edit.create(
                            model= self.Model,
                            input= prompt_body,
                            instruction= self.Instruction, #if not is_instruct_mode, should be ""
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
    def Get_PriceEstimate(self, len_prompt__tokens_est:int) -> float:
        est_cost__USD = self.price_in*(self.len_Instruction__tokens  + len_prompt__tokens_est) + self.price_out*len_prompt__tokens_est 
        return est_cost__USD

def GetLineRange(lines:List[int],nlines:int) -> Tuple[int,int]:
    #take a tuple of (min_line,max_line) from argparse -ln --lines. Starting line is 0, defaut is -1
    #and format these into an actual line range (start at 0) that won't run off the end of the file.
    min_line = min(max(0,lines[0]-1), nlines) #clamp to 0..nlines
    max_line = lines[1] 
    if max_line <=0: #handle default case of -1 refering to the end of the file
        max_lines = nlines
    else:
        max_line = min(max(max_line,min_line),nlines)
    return min_line, max_line


def GetPromptSingleFile(\
        prolog_cmdln_prompt_is_provided: bool, prolog_cmdln_prompt: str,\
        file_is_provided: bool, file_path: str,\
        epilog_cmdln_prompt_is_provided: bool, epilog_cmdln_prompt: str, prompt_type:str,\
        raw_line_range=(-1,-1)) -> Tuple[str,str,str]:
    #Example Use:
    #Instruction = GetPromptSingleFile(bool(args.file_path), args.file_path, bool(args.prompt_inst), args.prompt_inst, "instruction")
    #raw_line_range is a 2-long tuple of ints, it indicates a range of lines in the file, with line numbers that 
    #   starts at 1 so that it can be read out of a text editor and line range is inclusive. 
    #Returns file_prolog, Prompt, file_epilog 
    #   Prompt: prolog \n file_contents[raw_line_range] \n epilog
    #   file_prolog: file_contents[0:raw_line_range[0]], don't take the index litterally
    #   file_epilog: file_contents[raw_line_range[1]:end], don't take the index litterally
    newline_dict = {True:'',False:'\n'}
    file_prolog = ""
    Prompt = ""
    file_epilog = ""
    if prolog_cmdln_prompt_is_provided:
        Prompt = newline_dict[Prompt == ""] + prolog_cmdln_prompt
    if file_is_provided: 
            if not os.path.exists(file_path):
                print(f"Error: {prompt_type} file not found: {file_path}")
                sys.exit()
            with open(file_path, 'r', encoding=Encoding, errors='ignore') as fin:
                lines = fin.readlines()
                min_line, max_line = GetLineRange(raw_line_range,len(lines))
                file_prolog += ''.join(lines[:min_line])
                Prompt += newline_dict[Prompt == ""] + ''.join(lines[min_line:max_line])
                file_epilog += ''.join(lines[max_line:])
    if epilog_cmdln_prompt_is_provided:
        Prompt = newline_dict[Prompt == ""] + epilog_cmdln_prompt
    if Prompt == "":
        print("Error: {prompt_type} prompt is required, none was given. Exiting.")
        sys.exit()
    return file_prolog, Prompt, file_epilog 
    

def GetPromptMultipleFiles(prolog_cmdln_prompt_is_provided:bool, prolog_cmdln_prompt:str,\
        files_are_provided:bool, file_paths: List[str],\
        epilog_cmdln_prompt_is_provided:bool, epilog_cmdln_prompt:str, prompt_type:str) -> str:
    #Example Use:
    #Instruction = GetPrompt(False,'',bool(args.file_paths), args.file_paths, bool(args.prompt_inst), args.prompt_inst, "instruction")
    newline_dict = {True:'',False:'\n'}
    Prompt = ""
    if prolog_cmdln_prompt_is_provided:
        Prompt += newline_dict[Prompt == ""] + prolog_cmdln_prompt
    if files_are_provided: 
        for fname in file_paths:
            if not os.path.exists(fname):
                print(f"Error: {prompt_type} file not found: {fname}")
                sys.exit()
            with open(fname, 'r', encoding=Encoding, errors='ignore') as fin:
                Prompt += newline_dict[Prompt == ""] + fin.read() 
    if epilog_cmdln_prompt_is_provided:
        Prompt += newline_dict[Prompt == ""] + epilog_cmdln_prompt
    if Prompt == "":
        print("Error: {prompt_type} prompt is required, none was given. Exiting.")
        #Prompt = "In a bash program that calls GPT-3, the user forgot to input a prompt string. Say something cute to remind the user to     write a prompt string " 
        sys.exit()
    return Prompt

def get_front_white_idx(text:str) -> str: #tested
    #ret int indx of front white space
    l=len(text)
    for i in range(l):
        if not text[i].isspace():
            return i
    return l

def humanize_seconds(sec:Union[int,float]) -> str:
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

def get_back_white_idx(text:str, char_strt:int=0) -> int: #tested
    #ret int indx of back white space, starting from char 
    l=len(text)
    L=l-char_strt
    if L==0:
        return l
    for i in range(1,L):
        if not text[-i].isspace():
            return l-i+1
    return char_strt

def rechunk(text:str, len_text:int, chunk_start:int, chunk_end:int) -> int: #TO_TEST
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

class Process_Controler:
    def __init__(self):
        self.echo:bool = False
        self.is_test_mode:bool = False
        self.test_mode_max_chunks:int = 999 
        self.verbosity:Verb = Verb.normal
        self.output_file_is_set:bool = False
        self.bodyPrompt_file_is_set:bool = False
        self.output_filename:str = "gptoutput.txt"
        self.backup_output_filename:str = "gtpoutput_noDiff_backup.txt"
        self.bodyPrompt_filename:str = ""
        self.backup_bodyPrompt_filename:str = "OrigPromptBackup.txt"
        self.mac_mode = False
        if sys.platform == "darwin":
            self.mac_mode = True

    def Set_Echo(self,echo:bool) -> None:
        self.echo = echo
    def Set_Test_Chunks(self,test_mode_max_chunks:int):
        self.is_test_mode = (test_mode_max_chunks >= 0)
        self.test_mode_max_chunks = 999 
    def Set_Verbosity(self, verbosity:Verb) -> None:
        if self.is_test_mode and verbosity <= Verb.notSet:
            self.verbosity = Verb.test
        elif verbosity == Verb.notSet:
            self.verbosity = Verb.normal
        else:
            self.verbosity = verbosity
    def Set_Files(self, output_file_is_set : bool, output_filename,
            bodyPrompt_file_is_set : bool, bodyPrompt_filename) -> None:
        self.output_file_is_set = output_file_is_set
        self.output_filename = output_filename
        self.bodyPrompt_file_is_set = bodyPrompt_file_is_set
        self.bodyPrompt_filename = bodyPrompt_filename
        if output_file_is_set:
            prefix, extension = parse_fname(output_filename)
            self.backup_output_filename = prefix+"__noDiff_backup"+extension
            if not bodyPrompt_file_is_set:
                self.backup_bodyPrompt_filename = prefix+"__OrigPromptBackup"+extension
        if bodyPrompt_file_is_set:
            prefix, extension = parse_fname(bodyPrompt_filename)
            self.bodyPrompt_filename = bodyPrompt_filename
            self.backup_bodyPrompt_filename = prefix+"__OrigPromptBackup"+extension

    def MakeOkRejectFiles(self) -> None: 
        ok_file:str = "ok"
        reject_file:str = "reject"
        overwrite_bodyPrompt_with_GPT_output:bool = self.bodyPrompt_file_is_set and not (self.output_file_is_set or self.is_test_mode)
        with open(ok_file,'w') as fs:
            if overwrite_bodyPrompt_with_GPT_output:
                fs.write(f"mv {self.output_filename} {self.bodyPrompt_filename}\n" ) 
            fs.write(f"rm {self.backup_output_filename}\n")
            fs.write(f"rm {self.backup_bodyPrompt_filename}\n") #the backup copy of the complete prompt
            fs.write(f"rm {reject_file}\n")
            fs.write(f"rm {ok_file}\n")
        
        with open(reject_file,'w') as fs:
            fs.write(f"rm {self.output_filename}\n" )
            fs.write(f"rm {self.backup_output_filename}\n")
            fs.write(f"rm {self.backup_bodyPrompt_filename}\n")
            fs.write(f"rm {ok_file}\n")
            fs.write(f"rm {reject_file}\n")
    
        if self.verbosity > Verb.birthDeathMarriage:
            if overwrite_bodyPrompt_with_GPT_output:
                print(f"\nAfter meld/vimdiff, accept changes with \n$ sc {ok_file}\nwhich cleans temp files, and overwrites the input file {self.bodyPrompt_filename} with the output {self.output_filename}")
            else:
                print(f"\nAfter meld/vimdiff, accept changes with \n$ sc {ok_file}\nwhich cleans temp files. Final result is {self.output_filename}.")
            print("or reject changes with $ sc {reject_file}")
    def OpenOutputInTextEditor(self) -> None:
        if self.mac_mode:
            os.system(f"open -a textEdit {self.output_filename} &")
        else:
            os.system(f"{notepad_exe_file_path} {self.output_filename} &")
    def DoFileDiff(self) -> None:
        global meld_exe_file_path
        #body input is already copied to bodyPrompt_filename
        os.system("cp "+self.output_filename+" "+self.backup_output_filename+" &")
        
        if self.mac_mode:
            os.system(f"open -a Meld {self.bodyPrompt_filename} {self.output_filename} &")
        elif os.path.exists(meld_exe_file_path):
            meld_exe_file_path_callable = meld_exe_file_path.replace(" ", "\ ")
            os.system(f"{meld_exe_file_path_callable} {self.bodyPrompt_filename} {self.output_filename} &")
        else:
            print(f"Meld not found at path {meld_exe_file_path}. Try vimdiff or diff manually")
        """    try:
                os.system("vimdiff --version")
                os.system("vimdiff " + self.bodyPrompt_filename +" "+self.output_filename+" &")
            except:
                print("vimdiff not found, resorting to diff :-/ ")
                os.system("diff " + self.bodyPrompt_filename +" "+self.output_filename+" &")
                """
        if self.verbosity > Verb.birthDeathMarriage:
            print(f"vimdiff {self.bodyPrompt_filename} {self.output_filename}")
            print("If you have a meld alias setup:")
            print(f"meld {self.bodyPrompt_filename} {self.output_filename} &")

##### END PROCESS_CONTROLER ###########

def Process_Chunk(chunk_start:int, body_prompt:str, len_body_prompt__char:int, i_chunk:int, expected_n_chunks:int, MC:Model_Controler, PC:Process_Controler):
                chunk_end = chunk_start + tcl.guess_token_truncate_cutint_safer(body_prompt[chunk_start:], MC.maxInputTokens)
                chunk_end = rechunk(body_prompt,len_body_prompt__char, chunk_start, chunk_end)
                chunk_length__char = chunk_end - chunk_start
                chunk_length__tokens_est = tcl.nchars_to_ntokens_approx(chunk_length__char )
                chunk = body_prompt[chunk_start : chunk_end]
                frac_done = chunk_end/len_body_prompt__char
                if PC.verbosity >= Verb.normal:
                    print(f"i_chunk {i_chunk} of ~{expected_n_chunks }, chunk start at char {chunk_start} ends at char {chunk_end} (diff: {chunk_length__char} chars, est {chunk_length__tokens_est } tokens). Total body_prompt length: {len_body_prompt__char} characters, moving to {100*frac_done:.2f}% of completion") 
                if PC.echo or PC.verbosity >= Verb.hyperbarf:
                    print(f"Body prompt Chunk {i_chunk} of ~{expected_n_chunks }:")
                    print(chunk)
                if PC.verbosity >= Verb.normal:
                    print(f"{100*chunk_start/len_body_prompt__char:.2f}% completed. Processing i_chunk {i_chunk} of ~{expected_n_chunks}...") 
                chunk_start = chunk_end

                front_white_idx = get_front_white_idx(chunk)
                chunk_front_white_space = chunk[:front_white_idx ]
                chunk_end_white_space = chunk[get_back_white_idx(chunk,front_white_idx):]
                stripped_chunk = chunk.strip()
                
                ntokens_in = 0
                ntokens_out = 0
                if MC.disable_openAI_calls:
                     altchunk_course = chunk
                else:
                    #LLM CALL 
                    altchunk_course, ntokens_in, ntokens_out = MC.Run_OpenAI_LLM(chunk)

                altchunk = chunk_front_white_space +altchunk_course.strip() + chunk_end_white_space 

                if ntokens_in > 0 and PC.verbosity != Verb.silent:
                    prop = abs(ntokens_in-ntokens_out)/ntokens_in
                    if prop < 0.6:
                        print(f"Warning: short output. Looks like a truncation error on chunk {i_chunk}. Tokens in: {ntokens_in}, tokens out: {ntokens_out}.")
                    elif prop > 1.5:
                        print(f"Warning: weirdly long output on chunk {i_chunk}. Tokens in: {ntokens_in}, tokens out: {ntokens_out}.")

                if PC.verbosity >= Verb.normal:
                    if PC.verbosity >= Verb.debug: 
                         altchunk += f"\nEND CHUNK {i_chunk}. Tokens in: {ntokens_in}, tokens out: {ntokens_out}.\n"
                    print(f"That was prompt chunk {i_chunk}, it was observed to be {ntokens_in} tokens (apriori estimated was {chunk_length__tokens_est } tokens).\nResponse Chunk {i_chunk} (responce length {ntokens_out} tokens)")

                return altchunk, chunk_start 

def Loop_LLM_to_file(body_prompt:str, MC:Model_Controler, PC:Process_Controler, len_body_prompt__char:int = -1, Prologue:str = "", Epilogue:str="") -> None: 
    #Prologue and Epilogue get written to the file before and after the output of the GPT loop. Use this to just operate on a line range.
    if len_body_prompt__char == -1:
        len_body_prompt__char = len(body_promt)
    with open(PC.output_filename,'w') as fout:
        if Prologue != "":
            fout.write(Prologue)

        if not MC.disable_openAI_calls:
            openai.api_key = os.getenv("OPENAI_API_KEY")
            
        expected_n_chunks = tcl.count_chunks_approx(len_body_prompt__char, MC.maxInputTokens )
        chunk_start:int = 0
        i_chunk:int = 0
        t_start0 = time.time()

        while chunk_start < len_body_prompt__char:
                if PC.is_test_mode: 
                    if i_chunk >= PC.test_mode_max_chunks:
                        if PC.verbosity > Verb.silent:
                             print("\n Output terminated by test option")
                        break

                t_start = time.time()

                altchunk, chunk_start = Process_Chunk(chunk_start, body_prompt, len_body_prompt__char, i_chunk, expected_n_chunks, MC, PC)
                if PC.is_test_mode and i_chunk >= PC.test_mode_max_chunks -1:
                    altchunk += "\n Output terminated by test option"

                fout.write(altchunk)
                i_chunk += 1

                if i_chunk > expected_n_chunks*1.5: #nchunk based loop timout
                        if PC.verbosity != Verb.silent:
                            print(f"Error: Loop ran to chunk {i_chunk} while {expected_n_chunks} chunks were expected. That seems too long. Breaking loop.")
                        break

                if PC.echo or PC.verbosity >= Verb.hyperbarf:
                    total_run_time_so_far = time.time() - t_start0
                    total_expected_run_time = total_run_time_so_far/frac_done 
                    completion_ETA = total_expected_run_time - total_run_time_so_far
                    suffix = f"Chunk process time {humanize_seconds(time.time() - t_start)}. Total run time: {humanize_seconds(total_run_time_so_far)} out of {humanize_seconds(total_expected_run_time)}. Expected finish in {humanize_seconds(completion_ETA)}\n" 
                    print(altchunk + suffix)
        if Epilogue != "":
            fout.write(Epilogue)

def Loop_LLM_to_str(body_prompt:str,  MC:Model_Controler, PC:Process_Controler, len_body_prompt__char:int = -1) -> Tuple[str,bool]: 
        #Returns a LLM output looped over body_promt, and a bool saying if the processes terminated normally
        if len_body_prompt__char == -1:
            len_body_prompt__char = len(body_promt)
        output_str = ""
        if not MC.disable_openAI_calls:
            openai.api_key = os.getenv("OPENAI_API_KEY")
            
        expected_n_chunks = tcl.count_chunks_approx(len_body_prompt__char, MC.maxInputTokens )
        chunk_start:int = 0
        i_chunk:int = 0
        t_start0 = time.time()

        while chunk_start < len_body_prompt__char:
                if PC.is_test_mode:  #test_mode chunk limiter
                    if i_chunk >= PC.test_mode_max_chunks:
                        output_str += "\n Output terminated by test option"
                        if PC.verbosity > Verb.silent:
                             print("\n Output terminated by test option")
                        return output_str, True

                t_start = time.time()

                altchunk, chunk_start = Process_Chunk(chunk_start, body_prompt, len_body_prompt__char, i_chunk, expected_n_chunks, MC, PC)
                output_str += altchunk
                i_chunk += 1

                if i_chunk > expected_n_chunks*1.5: #nchunk based loop timout
                        if PC.verbosity != Verb.silent:
                            print(f"Error: Loop ran to chunk {i_chunk} while {expected_n_chunks} chunks were expected. That seems too long. Breaking loop.")
                        output_str += "\n Error: Output terminated by nchunk limiter"
                        return output_str, False

                if PC.echo or PC.verbosity >= Verb.hyperbarf:
                    total_run_time_so_far = time.time() - t_start0
                    total_expected_run_time = total_run_time_so_far/frac_done 
                    completion_ETA = total_expected_run_time - total_run_time_so_far
                    suffix = f"Chunk process time {humanize_seconds(time.time() - t_start)}. Total run time: {humanize_seconds(total_run_time_so_far)} out of {humanize_seconds(total_expected_run_time)}. Expected finish in {humanize_seconds(completion_ETA)}\n" 
                    print(altchunk + suffix)
        return output_str, True
