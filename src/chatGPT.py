import os, sys
import openai
#from https://community.openai.com/t/build-your-own-ai-assistant-in-10-lines-of-code-python/83210
#System prompts can be fed in as a command-line argument. If no argument is give, a boring default is used.

#Default system prompt 
System_Prompt = "You are a helpful assistant." 
#System_Prompt = "You are a professional language editor and text corrector for a science laboratory. Assist the user in creating professional high quality American English text for a scientific publications." #"DIRECTIVE_FOR_gpt-3.5-turbo"
#System_Prompt = "You are a German teacher and cultural advisor. Assist the user, who is an English speaking student just beginning to learn German language and Culture, to learn about the German language and culture." 

#Take a system prompt as a commandline argument if provided
if len(sys.argv) >= 2:
    print("System:",sys.argv[1])
    System_Prompt = sys.argv[1]

#Model = "gpt-3.5-turbo" #ChatGPT
Model = "gpt-4-0613" #If this works for you, call me. We'll throw a party.
#Model = "gpt-4" #If this works for you, call me. We'll throw a party.

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
print("Loaded OPENAI_API_KEY", OPENAI_API_KEY[:6]+"..."+OPENAI_API_KEY[-6:])
openai.api_key = OPENAI_API_KEY 

message = {"role":"user", "content": input("This is the beginning of your chat with AI. [To exit, send \"###\".]\n\nYou: ")};

conversation = [{"role": "system", "content": System_Prompt}]

while(message["content"]!="###"):
    conversation.append(message)
    completion = openai.ChatCompletion.create(model=Model, messages=conversation)
    message["content"] = input(f"\n\nAssistant: {completion.choices[0].message.content} \n\nYou: ")
    conversation.append(completion.choices[0].message)
