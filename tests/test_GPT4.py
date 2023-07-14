import os, sys
import openai
#from https://community.openai.com/t/build-your-own-ai-assistant-in-10-lines-of-code-python/83210
#System prompts can be fed in as a command-line argument. If no argument is give, a boring default is used.

print("This is a test of whether gpt-4 is accessible. If it is, it should have a conversation. If it isn't, expect an error like 'openai.error.InvalidRequestError: The model: `gpt-4` does not exist'")

System_Prompt = "You are a having a polite conversation." 

Model = "gpt-4" #If this works for you, call me. We'll throw a party.

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
print("Loaded OPENAI_API_KEY", OPENAI_API_KEY[:6]+"..."+OPENAI_API_KEY[-6:])
openai.api_key = OPENAI_API_KEY 

print("Type #### to exit")
print(f"System: {System_Prompt}")

user1 = "Hello, how are you today?"
print(f"User: {user1}")
message = {"role":"user", "content": user1};

conversation = [{"role": "system", "content": System_Prompt}]

while(message["content"]!="###"):
    conversation.append(message)
    completion = openai.ChatCompletion.create(model=Model, messages=conversation)
    message["content"] = input(f"\n\nAssistant: {completion.choices[0].message.content} \n\nYou: ")
    conversation.append(completion.choices[0].message)
