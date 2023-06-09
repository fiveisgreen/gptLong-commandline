import os
import openai
#This is maximally simple test of the openAI interface API operation. 

#Model = "gpt-4" #If this works for you, call me. We'll throw a party.
#Model = "gpt-3.5-turbo" #ChatGPT
#Model = "text-embedding-ada-002"
Model = "text-davinci-003" #GPT-3
#Model = "code-davinci-002"
#Model = "text-davinci-002" "GPT-2

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY 
print("Loaded OPENAI_API_KEY", OPENAI_API_KEY)

Prompt = "What is the capital of Africa?"
print("Prompt", Prompt)

Response = openai.Completion.create( model=Model, prompt=Prompt)

print("Response:")
print(Response.choices[0].text) 
#Correct behavior: A responce from the AI saying there is no one capital of Africa
#Incorrect output: Crashing, probalby with an openAI.error.AuthenticationError

