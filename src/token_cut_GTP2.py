from transformers import GPT2Tokenizer #pip install transformers
#from transformers import GPT2TokenizerFast #pip install transformers
import token_cut_light

#Written by Anthony Barker, December 21, 2022
#This starts up very slowly because of the GPT2TokenizerFast line, but then runs faster.
#Quick rule of thumb: n_characters = n_token * e + 2

tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
#tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
def count_tokens(text): #tested.
	#returns a count of the number of tokens in text.
	return len(tokenizer(text)['input_ids']) 

def token_truncate(text, maxTokens): #tested
	#returns the start of text such that it has maxTokens tokens 
	Cg = token_truncate_cutint(text, maxTokens)
	return text[:Cg]

def token_truncate_cutint(text, maxTokens): #tested
	#returns text index s.t. tokens(text[:text_index]) is the larges possible value <= maxTokens
	if maxTokens <= 0:
		return 0

	#Binary tree vars
	Cmax = len(text) #C's are cut value for text[:Chi] 
	Clo = 0
	Chi = Cmax 
	Cg = min(Cmax,token_cut_light.ntokens_to_nchars_approx(maxTokens)) #Cg = min(Cmax,int(maxTokens*2.718281828 + 2)) 
	Thi = count_tokens(text) 
	Tlo = 0 #T's track numbers of tokens
	Tg = count_tokens(text[:Cg]) 

	if Thi <= maxTokens: #If there are less tokens in the text than maxTokens
		return Cmax #no cut, just include all the text

	#Now have to truncate, begin bniary search
	#Algorithm Tune Parameters
	n = 8 #while timeout clock for binary search
	token_proximity = 1 #how far before maxTokens do we stop the binary search and start linearly stepping
	walk_range = 5 #int((token_proximity+1)*avg_char_per_token) 

	#Binary tree Search
	while  Tg > maxTokens or Tg < maxTokens - token_proximity:
		if Tg > maxTokens: #if Tg is too high, Cg guess is too high, go = "lo" #debug #hi's don't move
			Chi = Cg
			Thi = Tg
			Cg = max(0, Cg + min(-1,int( float((maxTokens - Tg)*(Cg - Clo)) / float(Tg - Tlo) ))) #should decrease Cg
		else: #Tg is too low, Cg guess is too low, go = "hi" #debug #lo's don't move
			Clo = Cg
			Tlo = Tg
			Cg = min(Cmax, Cg + max(1,int( float((maxTokens - Tg)*(Chi - Cg)) / float(Thi - Tg) ) ) )
		Tg = count_tokens(text[:Cg]) 
		n -= 1
		if n <= 0:
			break
	#now Tg should be a little less than maxTokens. 
	#now linearly step one character at a time to get to maxTokens. 
	#If any of those characters are \n, end after that.
	for i in range(walk_range):
		if Tg == maxTokens or text[min(Cmax,Cg+i)-1] == '\n': 
			Cg += i 
			break
		elif Tg > maxTokens: #went too far, go back to previous i.
			assert i > 0 ,"warning! Turncation did not converge somehow! Investigate" 
			Cg += i -1
			break
		Tg = count_tokens( text[:min(Cmax,Cg+i+1)] ) 
	
	return Cg
