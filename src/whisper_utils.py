import os
import tempfile
import math
import subprocess
import importlib

import openai
#from pydub import AudioSegment #This may be imported later
#from moviepy.editor import VideoFileClip #This may be imported later

from gpt_utils import Verb

"""
#most basics
file_path = "/mnt/c/Users/abarker/Downloads/OBS_audio.mp3"
f = open(file_path, "rb")
Prompt="This is a song. Transcribe both lyrics and non-sence (Woo Woo) words in the song."
transcript = Whisper_Call(f, Prompt)

##TODO: 
 - [ ]  add conversions for mp4, mpeg, mpga, m4a, and webm 
"""

Whisper_Max_Chunk_Size__MB = 25

def install_dependency(package_name):
    try:
        importlib.import_module(package_name)
    except ImportError:
        print(f"{} not found. Installing it...")
        subprocess.check_call(["pip","install",package_name])
        print(f"end installation effort for {package_name} package")

def get_Price(audio_length_ms):
    #The price in dollars of transcribing this audio
    audio_length_s = round(audio_length_ms/1000.,0)
    return 0.006*audio_length_s  #see https://openai.com/pricing

def is_openAI_audio_format(Format:str)->bool:
    ok_formats = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
    return Format.lower() in ok_formats

def is_pydub_audio_format(Format:str)->bool:
    ok_formats = [ "mp3", "wav", "ogg", "flac", "aac", "wma", "aiff","raw","pcm","au"]
        #[".mp3", ".wav", ".au", ".ogg", flac]
        #from source code: wav, raw, pcm, and possibly everything accepted by ffmpeg/avconv
    return (Format.lower() in ok_formats) or is_FFMPEG_audio_format(Format) 
    #it looks like pydub.AudioSegment.from_file takes raw, pcm, and everything that FFMPEG takes. Not sure though

def is_FFMPEG_audio_format(Format:str)->bool:
    #generated from $ ffmpeg -formats
    ok_formats = ["3dostr","3g2","3gp","4xm","a64","aa","aac","ac3","acm","act","adf","adp","ads","adts","adx","aea","afc","aiff","aix","alaw","alias_pix","alsa","amr","amrnb","amrwb","anm","apc","ape","apng","aptx","aptx_hd","aqtitle","asf","asf_o","asf_stream","ass","ast","au","avi","avisynth","avm2","avr","avs","avs2","bethsoftvid","bfi","bfstm","bin","bink","bit","bmp_pipe","bmv","boa","brender_pix","brstm","c93","caca","caf","cavsvideo","cdg","cdxl","chromaprint","cine","codec2","codec2raw","concat","crc","dash","data","daud","dcstr","dds_pipe","dfa","dhav","dirac","dnxhd","dpx_pipe","dsf","dsicin","dss","dts","dtshd","dv","dvbsub","dvbtxt","dvd","dxa","ea","ea_cdata","eac3","epaf","exr_pipe","f32be","f32le","f4v","f64be","f64le","fbdev","ffmetadata","fifo","fifo_test","film_cpk","filmstrip","fits","flac","flic","flv","framecrc","framehash","framemd5","frm","fsb","g722","g723_1","g726","g726le","g729","gdv","genh","gif","gif_pipe","gsm","gxf","h261","h263","h264","hash","hcom","hds","hevc","hls","hnm","ico","idcin","idf","iec61883","iff","ifv","ilbc","image2","image2pipe","ingenient","ipmovie","ipod","ircam","ismv","iss","iv8","ivf","ivr","j2k_pipe","jack","jacosub","jpeg_pipe","jpegls_pipe","jv","kmsgrab","kux","latm","lavfi","libcdio","libdc1394","libgme","libopenmpt","live_flv","lmlm4","loas","lrc","lvf","lxf","m4v","matroska","matroska","webm","md5","mgsts","microdvd","mjpeg","mjpeg_2000","mkvtimestamp_v2","mlp","mlv","mm","mmf","mov","mov","mp4","m4a","3gp","3g2","mj2","mp2","mp3","mp4","mpc","mpc8","mpeg","mpeg1video","mpeg2video","mpegts","mpegtsraw","mpegvideo","mpjpeg","mpl2","mpsub","msf","msnwctcp","mtaf","mtv","mulaw","musx","mv","mvi","mxf","mxf_d10","mxf_opatom","mxg","nc","nistsphere","nsp","nsv","null","nut","nuv","oga","ogg","ogv","oma","openal","opengl","opus","oss","paf","pam_pipe","pbm_pipe","pcx_pipe","pgm_pipe","pgmyuv_pipe","pictor_pipe","pjs","pmp","png_pipe","ppm_pipe","psd_pipe","psp","psxstr","pulse","pva","pvf","qcp","qdraw_pipe","r3d","rawvideo","realtext","redspark","rl2","rm","roq","rpl","rsd","rso","rtp","rtp_mpegts","rtsp","s16be","s16le","s24be","s24le","s32be","s32le","s337m","s8","sami","sap","sbc","sbg","scc","sdl","sdl2","sdp","sdr2","sds","sdx","segment","ser","sgi_pipe","shn","siff","singlejpeg","sln","smjpeg","smk","smoothstreaming","smush","sndio","sol","sox","spdif","spx","srt","stl","stream_segment","ssegment","subviewer","subviewer1","sunrast_pipe","sup","svag","svcd","svg_pipe","swf","tak","tedcaptions","tee","thp","tiertexseq","tiff_pipe","tmv","truehd","tta","tty","txd","ty","u16be","u16le","u24be","u24le","u32be","u32le","u8","uncodedframecrc","v210","v210x","vag","vc1","vc1test","vcd","vidc","video4linux2","v4l2","vividas","vivo","vmd","vob","vobsub","voc","vpk","vplayer","vqf","w64","wav","wc3movie","webm","webm_chunk","webm_dash_manifest","webp","webp_pipe","webvtt","wsaud","wsd","wsvqa","wtv","wv","wve","x11grab","xa","xbin","xmv","xpm_pipe","xv","xvag","xwd_pipe","xwma","yop","yuv4mpegpipe"]
    return Format.lower() in ok_formats
#currently mp4, mpeg, mpga, m4a, and webm files cannot be looped over since they are not pydub formats 
#TODO add conversion

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
"""What we learned: 
use 
from moviepy.editor import VideoFileClip
use for webm, m4a, 
video_clip = VideoFileClip(input_video_file)
audio_segment = video_clip.audio
audo_segment.export(output_mp3_file, format="mp3")

for mp4 inputs:
from moviepy.editor import AudioFileClip
video_clip = AudioFileClip(input_mp4_file)
audio_segment = AudioSegment.from_file(video_clip)
audio_segment.export(output_mp3_file, format="mp3")

should be able to use with just AudioClip with mp4, 
"""

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

def __Transcribe(input_file_path:str, output_file_path:str, Prompt:str, Temp:float=0.,Language:str='en',True_fileversion__False_strversion = False) -> str:
    #TODO vett file paths
    WC = Whisper_Controler()
    WC.Set_Temp(Temp)
    WC.Set_Instruction(Prompt)
    WC.Set_Language(Language)
    if True_fileversion__False_strversion:
        WC.Transcribe_loop_to_file(input_file_path, output_file_path, autodisable = True)
    else:
        return WC.Transcribe_to_str(input_file_path, autodisable = True) 

def Transcribe_to_str(input_file_path:str, Prompt:str, Temp:float=0.,Language:str='en') -> str:
    return __Transcribe_loop(input_file_path, "", Prompt, Temp,Language,False) 

def Transcribe_to_file(input_file_path:str, output_file_path:str, Prompt:str, Temp:float=0.,Language:str='en')->None:
    __Transcribe_loop(input_file_path, output_file_path, Prompt, Temp,Language,True) 

def Transcribe_to_file_simple(input_file_path:str, Prompt:str,Temp:float=0.,Language:str='en')->None:
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
        self.autodisable = True
        self.price = 0.006 #price in USD per sec of audio transcribed.
        self.echo:bool = False
    def Set_autodisable(self, autodisable:True)->None:
        self.autodisable = autodisable
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
    def whisper_call(binary_file_handle):
        transcript = ""
        if not self.disable:
            transcript = Whisper_Call(binary_file_handle, self.Instructions, self.Temp, "text", self.Language):
                """
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
            """
        return transcript 

        
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
            install_dependency("pydub")
            from pydub import AudioSegment
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
                        text = self.whisper_call(segment_v2)
                        if True_fileversion__False_strversion:
                            with open(output_file_path,'a') as fp:
                                fp.write(text + '\n')
                        else:
                            text.append(self.whisper_call(segment_v2))
        else: #small file that cannot use pydub, no loop
            with open(input_file_path, "rb") as audio:
                text = self.whisper_call(audio)
                if True_fileversion__False_strversion:
                    with open(output_file_path,'a') as fp:
                        fp.write(text + '\n')
                else:
                    text.append(self.whisper_call(segment_v2))
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
