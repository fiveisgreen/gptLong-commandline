import os
import openai
from pydub import AudioSegment
import tempfile
import math
from gpt_utils import Verb

"""
file_path = "/mnt/c/Users/abarker/Downloads/OBS_audio.mp3"
f = open(file_path, "rb")
Prompt="This is a song. Transcribe both lyrics and non-sence (Woo Woo) words in the song."
transcript = Whisper_Call(f, Prompt)
"""
Whisper_Max_Chunk_Size__MB = 25

def get_Price(audio_length_ms):
    #The price in dollars of transcribing this audio
    audio_length_s = round(audio_length_ms/1000.,0)
    return 0.006*audio_length_s  #see https://openai.com/pricing

def is_openAI_audio_format(Format:str)->bool:
    ok_formats = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
    return Format.lower() in ok_formats
def is_pydub_audio_format(Format:str)->bool:
    ok_formats = [ "mp3", "wav", "ogg", "flac", "aac", "wma", "aiff"]
    return Format.lower() in ok_formats


def Whisper_Call(binary_file_handle, Prompt, Temp=0, Responce_Format = "text", Language = "en"):
    """
    whisper is limited to 25MB chunks, so have to chunk with pydub:
    takes the audio file object (not file name) to transcribe, in one of these formats: mp3, mp4, mpeg, mpga, m4a, wav, or webm.
    see is_openAI_audio_format function
        https://platform.openai.com/docs/api-reference/audio/create#audio/create-prompt
    guesses for the rest of the API: https://github.com/openai/whisper/blob/248b6cb124225dd263bb9bd32d060b6517e067f8/whisper/transcribe.py#L36-L51

    Supplying the input language in ISO-639-1 format will improve accuracy and latency. 
        See https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
    Langages it's good at, in order, best first: #see https://github.com/openai/whisper
    Spanish (es), Italian (it), English (en), Portugese (pt), German (de); Japanese (ja), Polish (pl), Russian (ru)...
    And for the author's sake, Czech is "cs"
    """

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    openai.api_key = OPENAI_API_KEY 
    #print(f"Loaded OPENAI_API_KEY {OPENAI_API_KEY[:6]}..{OPENAI_API_KEY[-6:]}")

    transcript = openai.Audio.transcribe("whisper-1", binary_file_handle,
                initial_prompt=Prompt,
                temperature=Temp,
                response_format=Responce_Format,
                language=Language, #The language of the input audio. 
                #word_timestamps=True
                )
    return transcript 

def get_file_size_in_mb(file_path):
    file_size_in_bytes = os.path.getsize(file_path)
    file_size_in_mb = file_size_in_bytes / (1024 * 1024)
    return round(file_size_in_mb, 2)

def get_extension(filename):
    parts = filename.rsplit(".", 1)
    if len(parts) == 2:
        return parts[1] 
    else:
        return ""

def replace_extension(filename, new_extensions = "txt"):
    parts = filename.rsplit(".", 1)
    if len(parts) == 2:
        return parts[0] + "." + new_extensions
    else:
        return filename + "." + new_extensions

def Transcribe_loop_to_str(input_file_path:str, Prompt:str, Temp:float=0.,Language:str='en') -> str:
    global Whisper_Max_Chunk_Size__MB
    print(f"{input_file_path} -> {output_file_path}")
    Format = get_extension(input_file_path).lower()
    margin = 0.8 #ratio between the target segment size and the theoretical maximum
    file_size__MB = get_file_size_in_mb(input_file_path)
    audio = AudioSegment.from_file(input_file_path, format=Format)
    audio_length_ms=len(audio)
    print(f"Expected cost of this transcription: ${round(get_Price(audio_length_ms),3)}")
    dataRate_MB_per_ms = file_size__MB / (audio_length_ms)
    segment_length_ms = margin*Whisper_Max_Chunk_Size__MB/dataRate_MB_per_ms 
    text = []
    for i in range(0, math.ceil(audio_length_ms / segment_length_ms)):
        print(f"chunk {i+1} of {math.ceil(audio_length_ms / segment_length_ms)}")
        start = i * segment_length_ms
        end = min((i + 1) * segment_length_ms, audio_length_ms)
        segment = audio[start:end]

        #save this to file and immediately reopen it
        with tempfile.NamedTemporaryFile(suffix="."+Format) as f:
            segment.export(f.name, format=Format)

            with open(f.name, "rb") as segment_v2:
                text.append(Whisper_Call(segment_v2, Prompt, Temp, "text", Language))
    all_text = '\n'.join(text)
    print("done whispering")
    return all_text

def Transcribe_loop_to_file(input_file_path:str, output_file_path:str, Prompt:str, Temp:float=0.,Language:str='en')->None:
    global Whisper_Max_Chunk_Size__MB
    Format = get_extension(input_file_path).lower()
    margin = 0.8 #ratio between the target segment size and the theoretical maximum
    print(f"{input_file_path} -> {output_file_path}")
    file_size__MB = get_file_size_in_mb(input_file_path)
    audio = AudioSegment.from_file(input_file_path, format=Format)
    audio_length_ms=len(audio)
    print(f"Expected cost of this transcription: ${round(get_Price(audio_length_ms),3)}")
    dataRate_MB_per_ms = file_size__MB / (audio_length_ms)
    segment_length_ms = margin*Whisper_Max_Chunk_Size__MB/dataRate_MB_per_ms 
    for i in range(0, math.ceil(audio_length_ms / segment_length_ms)):
        print(f"chunk {i+1} of {math.ceil(audio_length_ms / segment_length_ms)}")
        start = i * segment_length_ms
        end = min((i + 1) * segment_length_ms, audio_length_ms)
        segment = audio[start:end]

        with tempfile.NamedTemporaryFile(suffix="."+Format) as f:
            segment.export(f.name, format=Format)
            with open(f.name, "rb") as segment_v2:
                text = Whisper_Call(segment_v2, Prompt, Temp, "text", Language)
                with open(output_file_path,'a') as fp:
                    fp.write(text + '\n')
    print("done whispering")

def Transcribe_loop_to_file_simple(input_file_path:str, Prompt:str,Temp:float=0.,Language:str='en')->None:
    #Writes a transcript file to the same filepath as the input, but as a txt file.
    output_file_path= replace_extension(input_file_path)
    Transcribe_loop_to_file(input_file_path, output_file_path, Prompt, Format,Temp,Language)

class Whisper_Controler:
    def __init__(self):
        self.disable_openAI_calls:bool = False #ok
        self.is_test_mode:bool = False #ok
        self.test_mode_max_chunks = 999 #ok
        self.input_safety_margin = 0.8 
        self.Instructions = "Transcribe this discussion" #Initial prompt for the transcription
        self.Language = 'en'
        self.Temp = 0
        self.verbosity=Verb.normal
        self.price = 0.006 #price in USD per sec of audio transcribed 
        self.echo:bool = False
    def Set_Echo(self,echo:bool) -> None:
        self.echo = echo
    def Set_disable_openAI_calls(self,disable:bool) -> None:
        self.disable_openAI_calls = disable
    def Set_Verbosity(self,verbosity:Verb) -> None:
        if self.is_test_mode and verbosity <= Verb.notSet:
            self.verbosity = Verb.test
        elif verbosity == Verb.notSet:
            self.verbosity = Verb.normal
        else:
            self.verbosity = verbosity
    def Set_Test_Chunks(self,test_mode_max_chunks:int):
        self.is_test_mode = (test_mode_max_chunks >= 0)
        self.test_mode_max_chunks = test_mode_max_chunks 
    def get_Price(audio_length_ms):
        #The price in dollars of transcribing this audio
        audio_length_s = round(audio_length_ms/1000.,0)
        return self.price*audio_length_s  #see https://openai.com/pricing
    def Discuss_Pricing_with_User(self, audio_length_ms:int, enable_user_prompt:bool = True, auto_disable:bool = True) -> None:
        est_cost__USD = self.get_Price(audio_length_ms)
        if self.verbosity >= Verb.birthDeathMarriage or (est_cost__USD > 0.1 and self.verbosity != Verb.silent):
            print(f"Expected cost of this transcription: ${round(get_Price(audio_length_ms),3):.3f}") 
            if enable_user_prompt and est_cost__USD > 0.5 and self.verbosity != Verb.silent:
                answer = input("Would you like to continue? (y/n): ")
                if not (answer.lower() == 'y' or answer.lower == 'yes'):
                    print("Disabling OpenAI API calls")
                    self.Set_disable_openAI_calls(True)
            elif auto_disable and not enable_user_prompt and est_cost__USD > 5:
                print("Automatically disabling OpenAI API calls")
                self.Set_disable_openAI_calls(True)
    def Set_Temp(self,temp:float) -> None:
        self.Temp = clamp(temp ,0.0,1.0)
    def Set_Instruction(self,Instructions:str) -> None:
        self.Instructions = Instructions
    def Set_Language(self,lang= 'en'):
        """Supplying the input language in ISO-639-1 format will improve accuracy and latency. 
            See https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
        Langages it's good at, in order, best first: #see https://github.com/openai/whisper
        Spanish (es), Italian (it), English (en), Portugese (pt), German (de); Japanese (ja), Polish (pl), Russian (ru)...
        And for the author's sake, Czech is "cs" """
        self.Language = lang
    def Set_Input_Safety_Margins( input_safety_margin:float ) -> None:
        self.input_safety_margin = input_safety_margin
    def Whisper_Call(binary_file_handle):
        """
        whisper is limited to 25MB chunks, so have to chunk with pydub:
        takes the audio file object (not file name) to transcribe, in one of these formats: mp3, mp4, mpeg, mpga, m4a, wav, or webm.
            https://platform.openai.com/docs/api-reference/audio/create#audio/create-prompt
        guesses for the rest of the API: https://github.com/openai/whisper/blob/248b6cb124225dd263bb9bd32d060b6517e067f8/whisper/transcribe.py#L36-L51
        """
        transcript = "lalala"
        if not self.disable:
            OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
            openai.api_key = OPENAI_API_KEY 
            if self.verbosity >= Verb.debug:
                print(f"Loaded OPENAI_API_KEY {OPENAI_API_KEY[:6]}..{OPENAI_API_KEY[-6:]}")
    
            transcript = openai.Audio.transcribe("whisper-1", binary_file_handle,
                    initial_prompt=self.Instructions,
                    temperature=self.Temp,
                    response_format="text",
                    language=self.Language
                    )
        return transcript 


    def Vet_FileType(self, Format:str, file_size__MB:float):
        #returns intermediate file type, used for export, as well as a bool saying whether looping can go on.
        global Whisper_Max_Chunk_Size__MB
        can_use_pydub_loop = True
        if is_pydub_audio_format(Format):
            if is_openAI_audio_format(Format): #happy go lucky land of mp3 and Wav
                Format_temp = Format
            else: #need to use export to conver to an openAI type
                Format_temp = "mp3" 
        else: #not a 
            if is_openAI_audio_format(Format): #can't do pydub
                if file_size__MB < Whisper_Max_Chunk_Size__MB:
                    #we can continue with this audio file since it's small and no looping is needed
                    can_use_pydub_loop  = False
                else:
                    print(f"Error! Cannot parse {Format} files over {Whisper_Max_Chunk_Size__MB} MB using pydub")
                    sys.exit()
            else:
                print(f"Error! Cannot handle this {Format} files")
                sys.exit()
        return Format_temp, can_use_pydub_loop 
        
    def Transcribe_loop_to_file(input_file_path:str, output_file_path:str, autodisable = True)->None:
        __Transcribe_loop(input_file_path, output_file_path, True)
    def Transcribe_to_str(self, input_file_path:str, autodisable = True) -> str:
        return __Transcribe_loop(input_file_path, "", False)

    def __Transcribe_loop(input_file_path:str, output_file_path:str="", True_fileversion__False_strversion = False, autodisable = True)->None:
        global Whisper_Max_Chunk_Size__MB
        if not os.path.exists(args.file):
            print(f"Error: file not found: {args.file}")
            sys.exit()
        file_size__MB = get_file_size_in_mb(input_file_path)
        Format = get_extension(input_file_path).lower()
        Format_temp, can_use_pydub_loop = Vet_FileType(Format, file_size__MB)
        if self.verbosity >= Verb.birthDeathMarriage:
            suffix = {True:"",False:f"by way of {Format_temp}"}[Format == Format_temp]
            print(f"Running Whisper({input_file_path}) -> {output_file_path}, Format = {Format}"+suffix)
        text = []
        if self.echo:
            if True_fileversion__False_strversion:
                with open(output_file_path,'a') as fp:
                    fp.write(f"Initial Prompt: {self.Instructions}\nTranscript:")
            else:
                text.append(f"Initial Prompt: {self.Instructions}\nTranscript:")
        if can_use_pydub_loop:
            audio = AudioSegment.from_file(input_file_path, format=Format)
            audio_length_ms=len(audio)
            Discuss_Pricing_with_User(audio_length_ms, self.verbosity > Verb.script), autodisable)
            dataRate_MB_per_ms = file_size__MB / (audio_length_ms)
            segment_length_ms = self.input_safety_margin*Whisper_Max_Chunk_Size__MB/dataRate_MB_per_ms 
            n_segments = math.ceil(audio_length_ms / segment_length_ms)
            for i in range(0, n_segments):
                if self.is_test_mode and i >= self.test_mode_max_chunks:
                    if self.verbosity >= Verb.test:
                        print(f"Test mode terminates at {i} segments")
                    break
                if self.verbosity >= Verb.normal:
                    print(f"chunk {i+1} of {n_segments}")
                start = i * segment_length_ms
                end = min((i + 1) * segment_length_ms, audio_length_ms)
                segment = audio[start:end]
                with tempfile.NamedTemporaryFile(suffix="."+Format_temp) as f:
                    segment.export(f.name, format=Format_temp)
                    with open(f.name, "rb") as segment_v2:
                        text = self.Whisper_Call(segment_v2)
                        if True_fileversion__False_strversion:
                            with open(output_file_path,'a') as fp:
                                fp.write(text + '\n')
                        else:
                            text.append(self.Whisper_Call(segment_v2))
        else: #small file that cannot use pydub, no loop
            with open(input_file_path, "rb") as audio:
                text = self.Whisper_Call(audio)
                if True_fileversion__False_strversion:
                    with open(output_file_path,'a') as fp:
                        fp.write(text + '\n')
                else:
                    text.append(self.Whisper_Call(segment_v2))
        if self.verbosity >= Verb.birthDeathMarriage:
            print("done whispering")
        if True_fileversion__False_strversion:
            return all_text = '\n'.join(text)

""" #Example use
filename = "input.mp3"
output_file = "output_Transcribe_loop.txt"
#Transcribe_loop_to_file(filename, output_file, "This is an interview with the biologist Michael Levin. Write the transcript")

all_text = Transcribe_loop(filename, "This is an interview with the biologist Michael Levin. Write the transcript")
with open(output_file,'w') as fp:
    fp.write(all_text)
"""

#file_path = "/mnt/c/Users/abarker/Downloads/OBS_audio.mp3"
#f = open(file_path, "rb")
#Prompt="This is a song. Transcribe both lyrics and non-sence (Woo Woo) words in the song."

#transcript  = wl.Whisper_Call(f,Prompt, Temp)

#print(transcript)
#outFilePath = "WhisperOutput.txt"
#with open(outFilePath,'w') as fout:
#    fout.write(transcript )

???END
