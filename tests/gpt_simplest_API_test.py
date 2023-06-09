import os
import openai
#This is maximally simple test of the openAI interface API operation. 

#Model = "gpt-4" #If this works for you, call me. We'll throw a party.
#Model = "gpt-3.5-turbo" #ChatGPT
#Model = "text-embedding-ada-002"
Model = "text-davinci-003" #GPT-3
#Model = "code-davinci-002"
#Model = "text-davinci-002" "GPT-2

Prompt = "What is the capital of Africa?"
print("Prompt", Prompt)

openai.api_key = os.getenv("OPENAI_API_KEY")
Response = openai.Completion.create( model=Model, prompt=Prompt)

print("Response:", Response.choices[0].text) 
#text-davinci-003 usally says there is no one capital of Africa

