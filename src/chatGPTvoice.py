import os, sys
import openai
from elevenlabs import generate, play, stream, set_api_key#, voices
from colorama import Fore, Back, Style

#from https://community.openai.com/t/build-your-own-ai-assistant-in-10-lines-of-code-python/83210
#Elevenlabs API documentation: https://github.com/elevenlabs/elevenlabs-python/blob/main/API.md

#TODO: 
# - [X] Get this working
# - [ ] Bring in argparse for echo on/off, voice ctrl, load/save
# - [X] Merge with chat, just by turning off voices.
# - [ ] Add load and save features
# - [X] Colorize output
# - [X] System prompts can be fed in as a command-line argument. If no argument is give, a boring default is used.

#Model = "gpt-3.5-turbo" #ChatGPT
Model = "gpt-4" 
max_char = 570

useStream = True
speak_user_input = True
speak_assistant_output = True
print_preamble = True
Voice_assistant = "Charles" #custom voice #"Dave"
Assistantname = Voice_assistant 

#Voice_user = "Anthony" #custom voice
Voice_user = "AnthonyBarker" #custom voice clone
Username = "Anthony"
#Voice_user = "Serena" #Jana's Personal
#Username = "Jana"

"""Useful Voices
Built-in voices:
name	 accent	description	 age	        gender	use case
Serena	 american	pleasant middle aged	female	interactive
Rachel	 american	calm	 young	        female	narration
Matilda	 american	warm	 young	        female	audiobook
Charlotte brit/swedish	seductive middle aged	female	video games
Grace	 amer-southern	gentle	 young	        female	audiobook
Arnold	 american	crisp	 middle aged	male	narration
Adam	 american	deep	 middle aged	male	narration
Antoni	 american	well-rounded young	male	narration
Liam	 american	neutral	 young	        male	narration
Dave	 british-essex	conversational young	male	video games
Giovanni brit-italian   foreigner young	        male	audiobook

My custom voices:
    Anthony, Charles
"""

#Default system prompt 
#System_Prompt = "You are a helpful assistant." 
#System_Prompt = "You are a professional language editor and text corrector for a science laboratory. Assist the user in creating professional high quality American English text for a scientific publications." #"DIRECTIVE_FOR_gpt-3.5-turbo"
System_Prompt = f"You are a German teacher and cultural advisor. Your name is {Assistantname}. Assist the user, who is an English speaking student just beginning to learn German language and Culture, to learn about the German language and culture. Teach through long-form conversation." 

#Take a system prompt as a commandline argument if provided
if len(sys.argv) >= 2:
    print(Fore.RED + "System:",sys.argv[1])
    System_Prompt = sys.argv[1]

#COLOR SCHEME
color_norm      = Style.RESET_ALL
color_sys       = Fore.RED  + Style.DIM 
color_start     = Fore.RED  + Style.NORMAL
color_sp        = Fore.CYAN + Style.NORMAL #system prompt
color_user      = Back.RESET + Fore.BLUE  + Style.NORMAL
color_assist    = Back.RESET + Fore.GREEN + Style.NORMAL
color_preuser   = Back.BLUE  + Fore.BLACK + Style.BRIGHT
color_preassist = Back.GREEN + Fore.BLACK + Style.BRIGHT
"""
print(Fore.RED + 'some red text')
print(Back.GREEN + 'and with a green background')
print(Style.DIM + 'and in dim text')
Fore: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
Back: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
Style: DIM, NORMAL, BRIGHT, RESET_ALL
"""

break_str = "###" #The string the user has to enter to end the conversation
seperator = color_norm+"\n\n"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY 

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
set_api_key(ELEVENLABS_API_KEY)

if print_preamble:
    print(color_sys + f"Loaded OPENAI_API_KEY={OPENAI_API_KEY[:6]}...{OPENAI_API_KEY[-6:]}"+ color_norm)
    print(color_sys + f"Loaded ELEVENLABS_API_KEY={ELEVENLABS_API_KEY[:6]}...{ELEVENLABS_API_KEY[-6:]}" + color_norm)
    #FOR DEV ONLY, REMOVE THESE TWO LINES FOR PRODUCTION
    onoff_str = {False:"off",True:"on"}[useStream]
    print(color_sys + f"Streaming is {onoff_str}" + color_norm)
    print(seperator)

def Play(audio_handle, useStream):
    #audio_handle may be raw audio or an audio stream
    #useStream: bool
    if useStream:
        stream(audio_handle)
    else:
        play(audio_handle)

def IsBreak(user_text, break_str):
    if user_text == break_str: 
        return True
    elif len(user_text.strip()) >= len(break_str):
        if user_text.strip()[:len(break_str)] == break_str:
            return True
    else:
        return False

max_Tokens = int(max_char/2.718)
user_text = input(color_start + f'This is the beginning of your chat with {Model}. Its instructions are: "' + color_sp + System_Prompt + color_start + '" [To exit, send "{break_str}".]' + seperator + color_preuser + Username + ':'+color_user+' ')

conversation = [{"role": "system", "content": System_Prompt}]
message = {"role":"user", "content": user_text };

if speak_user_input:
    Play(generate(text=user_text, voice=Voice_user, model="eleven_multilingual_v2", stream=useStream), useStream)

#while(not IsBreak(message["content"],break_str) ):
while(True):
    conversation.append(message)
    completion = openai.ChatCompletion.create(model=Model, messages=conversation,max_tokens= max_Tokens)
    """
     openai.ChatCompletion.create(
                        model= self.Model,
                        messages= conversation,
                        temperature= self.Temp,
                        #max_tokens= self.maxOutputTokens,
                        top_p= self.Top_p,
                        frequency_penalty= self.Frequency_penalty,
                        presence_penalty= self.Presence_penalty
                        )
    """
    completion_txt = completion.choices[0].message.content
    conversation.append(completion.choices[0].message)

    assist_output_str = seperator + color_preassist + Assistantname+':' + color_assist + ' '+completion_txt
    if speak_assistant_output:
        audio_handle = generate(text=completion_txt, voice=Voice_assistant, model="eleven_multilingual_v2", stream=useStream)
        print(assist_output_str)
        Play(audio_handle, useStream)
    else:
        print(assist_output_str)
    user_text = input(seperator + color_preuser + Username+':' + color_user + ' ')
    if IsBreak(user_text, break_str): 
        break
    message["content"] = user_text  
    if speak_user_input:
        Play(generate(text=user_text, voice=Voice_user, model="eleven_multilingual_v2", stream=useStream), useStream)

print(Style.RESET_ALL)
