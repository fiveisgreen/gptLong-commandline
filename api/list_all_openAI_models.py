import os
import openai
#This is maximally simple test of the openAI interface API operation. 

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY 
print(f"Loaded OPENAI_API_KEY {OPENAI_API_KEY[:6]}..{OPENAI_API_KEY[-6:]}")

models = openai.Model.list()
for moddat in models.data:
    print( moddat.id )

