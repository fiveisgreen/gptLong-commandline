from math import sqrt
from math import ceil
#Written by Anthony Barker, December 21, 2022
#Quick rule of thumb: n_characters = n_token * e + 2

avg_char_per_token = 2.718281828 #=e=math.exp(1) 
init_offset = 2

def nchars_to_ntokens_approx(nchars):
	return max(0,int((nchars - init_offset)*0.367879441)) #0.36...=1/e = 1/avg_char_per_token

def ntokens_to_nchars_approx(ntokens): #tested
	return max(0,int(ntokens*avg_char_per_token + init_offset ) ) 

def nchars_leq_ntokens_approx(maxTokens):
    """returns a number of characters very likely to correspond <= maxTokens"""
    #sqrt_margin = 0.5
    #lin_margin = 1.010175047 #= e - 1.001 - sqrt(1 - sqrt_margin) #ensures return 1 when maxTokens=1
    return max( 0, int(maxTokens*avg_char_per_token - 1.010175047 - sqrt(max(0,maxTokens - 0.5 ) ) )) 

def count_tokens_approx(text): #fast, doesn't need transformers #tested
	#given a text string, estimates how many tokens are in it.
	return nchars_to_ntokens_approx(len(text))

def count_chunks_approx(length_of_text, maxTokens_per_chunk): #untested
	return ceil( length_of_text / nchars_leq_ntokens_approx(maxTokens_per_chunk) ) 

#truncate_text_to_maxTokens_approx
def guess_token_truncate_cutint(text, ntokens): #tested
	#I don't know of any use for this now. Use guess_token_truncate_cutint_safer instead
	#given a text, returns the mean estimate of the character index to cut the text so it will have #tokens = maxTokens
	#results both too high and too low are common
	return min(len(text), ntokens_to_nchars_approx(ntokens)) 

def guess_token_truncate_cutint_safer(text, maxTokens): #fast, doesn't need transformers
	#given a text, conservatively guess where to cut it so that it'll be under maxTokens
	#it is very likely that the character cut gives #tokens <= maxTokens, but not guarenteed.
	return min( len(text), nchars_leq_ntokens_approx(maxTokens) )
	#which is to say:
	#sqrt_margin = 0.5
	#lin_margin = 1.010175047 #= avg_char_per_token - 1.001 - sqrt(1-sqrt_margin) #ensures return 1 when maxTokens=1
	#return min( len(text), max( 0, int(maxTokens*avg_char_per_token - lin_margin - sqrt(max(0,maxTokens - sqrt_margin) ) )) )

def truncate_text_to_maxTokens_approx(text, maxTokens):
    #returns a truncation of text to make it (likely) fit within a token limit
    #So the output string is very likely to have <= maxTokens, no guarantees though.
    char_index = guess_token_truncate_cutint_safer(text, maxTokens)
    return text[:char_index]

#########################
#########################
#########################
