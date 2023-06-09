import os, sys
import json
import openai
import argparse
import token_cut_light
from gpt import GPT

""" #################### USAGE AND EXAMPLES ###########################

###### Examples ######

$ gtpe "my instruction prompt" -f body_file [-o outfile]
$ gpte "my instruction prompt" "my body prompt to edit" 
$ gtpe -f body_file1 -i instr_file1 instr_file2 [-o outfile]

####### FUll Usage #######
$ gtpe ["instructions"] ["body epilog"] [-f body.txt] [-i instruction1.txt instrcution2.txt] [-o outfile.txt] [params] [flags]

Flags:
# -e --edit     switch engine to an edit oriented model
# -c --code     switch engine to code mode
# --old         switch engine from edit mode to merged prompt mode with instruction prolog.
# --echo     prints prompt and responce to terminal
# -v --verbose  turn on verbose printint
# -d --disable  disables GTP-3 call for debugging
# -v --version  print version.

Optional Model Parameters
-n              #max tokens of responce. -n scales it to body prompt length: -n*10%*body_prompt_length 
--top_p [0..1]  #Controls diversity. Default=1. 
--temp [0..1]   #Controls ramdomness, 0 = deterministic and repetitive.
-p [0..2]       #presence_penalty, turn up encourages discussion diversity. Use only with -g.
-q [0..2]       #frequency_penalty, turn up discourages repetition. Use only with -g. 

TODO:
    - [ ] fix the max_tokens mess
    - [ ] input tokens model dependent
    - [ ] use gpt-3.5-turbo
    - [ ] make inputToken_safety_margin a commandline parameter
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
inputToken_safety_margin = 0.8 #TODO set this as a commandline parameter

#Argparse 
#argparse documentation: https://docs.python.org/3/library/argparse.html
parser = argparse.ArgumentParser(description='''A basic command line parser for GPT3-edit mode''', epilog = '''Command-line interface written by Anthony Barker, 2022. The main strucutre was written primarily by Shreya Shankar, Bora Uyumazturk, Devin Stein, Gulan, and Michael Lavelle''', prog="gpt_command_prompt")
parser.add_argument("prompt_inst", nargs='?', help="Instruction prompt string. If both this and -i files are give, this goes after the file contents.")
parser.add_argument("prompt_body", nargs='?', help="Body prompt string. If both this and -f files are give, this goes after the file contents.") #broken

parser.add_argument("-f","--files", help="Prompt file of body text to be edited.") #"files" for historical reasons but there's at most 1 file.
parser.add_argument("-i", dest="instruction_files", nargs='+', help="Prompt files, to be used for edit instructions.") 
parser.add_argument("-o", dest="out", help="Responce output file", default = "gptoutput.txt")  

parser.add_argument('-e', '--edit', action='store_true', help='Uses the text-davinci-edit-001 model, which is older but oriented around  text editing')
parser.add_argument('-c', '--code', action='store_true', help='Uses the code-davinci-edit-001 model to optomize code quality. If combined with --old, uses code-davinci-002 with merged instruction and body and double the max input tokens')
parser.add_argument('--old', action='store_true', help='Use GTP-3 (text-davinci-003 / code-davinci-002) with merged instructions and prompt. Can be combined with the -c/--code flag.')

parser.add_argument("-n", dest="max_tokens", type=int, help="Maximum word count (really token count) of responce. Negative n will set max based on body prompt length, in units of 10%% of body prompt length. Max = -n*prompt_tokens/10. So -10 limits output to the body prompt length. -15 may be a good choice, limiting output to 150%% of body prompt length. In all cases,Max 4096.") 
#The point here is to make sure chatGPT doesn't runaway. But this is really dumb since it's most likely to produce unwanted truncation. 
parser.add_argument("--top_p", type=float, help="top_p parameter. Controls diversity via nucleus sampling. 0.5 means half of all likelihood-weighted options are considered. Clamped to [0,1]", default = 1.0) 
parser.add_argument("--temp", type=float, help="temperature parameter. Controls randomness. Lowering results in less random completions. As the temperature approaches zero, the model will become deterministic and repetitive. Clamped to [0,1]", default = 0) 
parser.add_argument("-q", dest="frequency_penalty", type=float, help="frequency_penalty parameter. How much to penalize new tokens based on their existing frequency in the text so far. Decreases the model's likelihood of repeating the same line verbatim. Clamped to [0,2]", default = 0)
parser.add_argument("-p", dest="presence_penalty", type=float, help="presence_penalty parameter. How much to penalize new tokens based on whether they appear in the text so far. Increaces the model's likelihood to talk about new topics. Clamped to [0,2]", default = 0)

parser.add_argument('--echo', action='store_true', help='Print Prompt as well as responce')
parser.add_argument('--verbose', action='store_true', help='Spew everything')
parser.add_argument('-d', '--disable', action='store_true', help='Does not send command to GPT-3, used for prompt design and development')
parser.add_argument("-v", "--version", action='version', version='%(prog)s 0.2.0') 

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
maxOutputTokens = 256 #meaningless placeholder.
Top_p= clamp(args.top_p ,0.0,1.0) #1.0
Temp = clamp(args.temp ,0.0,1.0) #0
Frequency_penalty = clamp(args.frequency_penalty ,0.0,2.0) #0
Presence_penalty = clamp(args.presence_penalty ,0.0,2.0) #0

######### Input Ingestion ##############

#Set Model
use_chatGPT = True
Model = "gpt-3.5-turbo"
maxInputTokens  = 4096 #max tokens that the model can handle, or max that you're willing to supply, probably can go to 4096
if args.old:
    if args.code:
        Model = "code-davinci-002"
        maxInputTokens = 8001 #https://platform.openai.com/docs/models/gpt-3-5
        use_chatGPT = False
    else:
        Model = "text-davinci-003"
        maxInputTokens = 4097 #https://platform.openai.com/docs/models/gpt-3-5
        use_chatGPT = False
    if args.frequency_penalty:
        print("Note that with -g/--gtp3, the frequency_penalty option does nothing")
    if args.presence_penalty:
        print("Note that with -g/--gtp3, the presence_penalty option does nothing")
elif args.code:
        Model = "code-davinci-edit-001"
        maxInputTokens = 4097 #pure guess
        use_chatGPT = False
elif args.edit:
        Model = "text-davinci-edit-001"
        maxInputTokens = 4097 #pure guess
        use_chatGPT = False


#make a safety margin on the input tokens
maxInputTokens = int(inputToken_safety_margin * maxInputTokens )

backup_gtp_file = "gtpoutput_backup.txt" 
#Body Prompt
"""if args.files:  #for multiple files -- more trouble than it's worth.
    for fname in args.files:
        if Prompt == "":
            with open(fname, 'r', encoding=Encoding) as fin:
                Prompt = fin.read() 
        else: 
            with open(fname, 'r', encoding=Encoding) as fin:
                Prompt += '\n' + fin.read() 
    if len(args.files) > 0: 
        prefix, extension = parse_fname(args.files[0])
        args.out = prefix+"__gtpMeld"+extension 
        backup_gtp_file = prefix+"__gtpRaw"+extension 
        prompt_fname = prefix+"__prmoptRaw"+extension """
output_file_set = False
if args.out:
    output_file_set = True

if args.files: 
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

#Instruction Prompt
if args.instruction_files: 
    for fname in args.instruction_files:
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

#Set maxOutputTokens
if args.max_tokens:
        if args.max_tokens < 0:
            Prompt_tokens = count_tokens_approx(Prompt) 
            maxOutputTokens = max(4096,int(-args.max_tokens*Prompt_tokens/10))
        else:
            maxOutputTokens = max(4096,args.max_tokens)
        
if args.verbose:
    print("Model: ",Model)
    print("maxInputTokens ",maxInputTokens )
    print("maxOutputTokens ",maxOutputTokens )
    print("Top_p",Top_p)
    print("Temp",Temp)

def get_front_white_idx(text): #tested
    #ret int indx of front white space
    l=len(text)
    for i in range(l):
        if not text[i].isspace():
            return i
    return l
    
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

#Main 
#def run_loop( in_file_name, out_file_name, gtp_instructions,  maxInputTokens = 4095):
with open(args.out,'w') as fout:
            if not args.disable:
                openai.api_key = os.getenv("OPENAI_API_KEY")
            len_prompt = len(Prompt)
            if args.verbose:
                print("length of prompt body", len_prompt ) 
            chunk_start = 0
            i_chunk = 0
            expected_n_chunks = token_cut_light.count_chunks_approx(len_prompt, maxInputTokens )

            while chunk_start < len_prompt:
                chunk_end = chunk_start + token_cut_light.guess_token_truncate_cutint_safer(Prompt, maxInputTokens) 
                chunk_end = rechunk(Prompt,len_prompt, chunk_start, chunk_end)
                if args.verbose:
                    print("i_chunk",i_chunk, "chunk start", chunk_start,"end",chunk_end ) 
                chunk = Prompt[chunk_start : chunk_end]
                if args.echo or args.verbose: 
                    print("Prompt Chunk:")
                    print(chunk)
                front_white_idx = get_front_white_idx(chunk)
                chunk_front_white_space = chunk[:front_white_idx ]
                chunk_end_white_space = chunk[get_back_white_idx(chunk,front_white_idx):]
                stripped_chunk = chunk.strip()
                
                #GPT-3 CALL 
                if args.disable:
                     altchunk_course = chunk
                else:
                    if use_chatGPT:
                        conversation = [{"role": "system", "content": Instruction}]
                        conversation.append({"role":"user", "content": chunk})
                        if args.max_tokens:
                            altchunk_course = openai.ChatCompletion.create(
                                    model=Model, 
                                    messages=conversation,
                                    temperature=Temp,
                                    max_tokens=maxOutputTokens,
                                    top_p=Top_p,
                                    frequency_penalty=Frequency_penalty,
                                    presence_penalty=Presence_penalty
                                    ).choices[0].message.content
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
                            altchunk_course = openai.ChatCompletion.create(
                                    model=Model, 
                                    messages=conversation,
                                    temperature=Temp,
                                    #max_tokens=maxOutputTokens,
                                    top_p=Top_p,
                                    frequency_penalty=Frequency_penalty,
                                    presence_penalty=Presence_penalty
                                    ).choices[0].message.content
                            """altchunk_course = openai.ChatCompletion.create(
                                    model=Model,
                                    messages=[{"role": "user", "content": Instruction+"\n\n"+chunk}],
                                    temperature=Temp,
                                    #max_tokens=maxOutputTokens,
                                    top_p=Top_p,
                                    frequency_penalty=Frequency_penalty,
                                    presence_penalty=Presence_penalty
                                    ).choices[0].message.content """
                    elif args.gpt3:
                        if args.max_tokens:
                            altchunk_course = openai.Completion.create(
                                    model=Model,
                                    prompt=Instruction+"\n\n"+chunk,
                                    temperature=Temp,
                                    max_tokens=maxOutputTokens,
                                    top_p=Top_p,
                                    frequency_penalty=Frequency_penalty,
                                    presence_penalty=Presence_penalty
                                    ).choices[0].text
                        else:
                            altchunk_course = openai.Completion.create(
                                    model=Model,
                                    prompt=Instruction+"\n\n"+chunk,
                                    temperature=Temp,
                                    #max_tokens=maxOutputTokens,
                                    top_p=Top_p,
                                    frequency_penalty=Frequency_penalty,
                                    presence_penalty=Presence_penalty
                                    ).choices[0].text
                    else:
                        if args.max_tokens:
                            altchunk_course = openai.Edit.create( 
                                    model=Model,
                                    input=chunk,
                                    instruction=Instruction,
                                    temperature=Temp,
                                    max_tokens=maxOutputTokens,
                                    top_p=Top_p).choices[0].text
                        else:
                            altchunk_course = openai.Edit.create(
                                    model=Model,
                                    input=chunk,
                                    instruction=Instruction,
                                    temperature=Temp,
                                    #max_tokens=maxOutputTokens,
                                    top_p=Top_p).choices[0].text
                altchunk = chunk_front_white_space +altchunk_course.strip() + chunk_end_white_space 
                #altchunk = chunk_front_white_space +altchunk_course.strip() + chunk_end_white_space+"@@@" #degug
                fout.write(altchunk)

                chunk_start = chunk_end
                i_chunk += 1

                if i_chunk > expected_n_chunks*1.5: #loop timout, for debug
                        print("loop ran to chunk",i_chunk, ". That seems too long. Breaking loop.")
                        break

                if args.echo or args.verbose:
                    print("Response Chunk:")
                    print(altchunk)

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

#gpt = GPT(engine="davinci", temperature=0.5, max_tokens=100)
#prompt = "Display the lowest salary from the Worker table."
#output = gpt.submit_request(prompt)
