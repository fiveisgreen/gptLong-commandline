import os, sys
import openai
import argparse
import time
from typing import Tuple
from gpt_utils import *
from whisper_utils import *

#example: 
#whisper input_file "my prompt"
#whisper input_file "my prompt" -o output_file

#TODO: 
#- [ ] test everything

"""SETTINGS"""
version_number__str = "0.1.0"

def setupArgparse():
    #argparse documentation: https://docs.python.org/3/library/argparse.html
    parser = argparse.ArgumentParser(description='''A basic command line parser for GPT3''', epilog = '''Command-line interface written by Anthony Barker, 2022. The main strucutre was written primarily by Shreya Shankar, Bora Uyumazturk, Devin Stein, Gulan, and Michael Lavelle''',prog="gpt_command_prompt")
    
    parser.add_argument(dest="file", type=str, help="Audio file path") 
    parser.add_argument("Prompt_cmdLnStr", type=str,  nargs='?', help="Initial prompt string for the transcription.") 
    parser.add_argument("-o", dest="out", help="Output transcript file. If none provided, default is the input file with the extension changed to .txt")  

    parser.add_argument("--temp", type=float, help="temperature parameter. Controls randomness. Lowering results in less random completions. As the temperature approaches zero, the model will become deterministic and repetitive. Clamped to [0,1]", default = 0) 
    parser.add_argument('--echo', action='store_true', help='Print Prompt as well as responce')
    parser.add_argument('--verbose', nargs='?', const=3, type=int, help='How verbose to print. 0 = silent.',default = -1)
    parser.add_argument('-t',"--test", nargs='?', const=2, type=int, help='Put the system in test mode for prompt engineering, which runs a limited number of audio segments that can be set here (default is 2). It also turns on some extra printing', default = -1)
    parser.add_argument('-d', '--disable', action='store_true', help='Does not send commands to openAI, used for prompt design and development')
    parser.add_argument("-v", "--version", action='version', version=f'%(prog)s {version_number__str}') 

    args = parser.parse_args() 
    return args

######### Input Ingestion ##############
args = setupArgparse()

input_file_path = ""
if args.file:
    input_file_path = args.file
else:
    print(f"Error: Input audio file required") 
    sys.exit()

output_file_path = ""
if args.out:
    output_file_path = args.out
else:
     output_file_path = replace_extension(args.file)

WC = Whisper_Controler()
if args.Prompt_cmdLnStr:
    WC.Set_Instruction(args.Prompt_cmdLnStr)
WC.Set_Temp(args.temp)
WC.Set_Echo(args.echo)
WC.Set_Verbosity(args.verbose, PC.is_test_mode ) 
WC.Set_Test_Chunks(arsg.test)
WC.Set_disable_openAI_calls(args.disable)
####### Run Whisper ############
WC.Transcribe_loop_to_file(input_file_path, output_file_path, autodisable = True)
    
#PC.OpenOutputInTextEditor()

