import os
import tempfile
import math
import subprocess
import importlib
from enum import auto, IntEnum

import openai
#from pydub import AudioSegment #This may be imported later
#from moviepy.editor import VideoFileClip #This may be imported later

from gpt_utils import Verb, clamp, parse_fname

"""
#most basics
file_path = "/mnt/c/Users/abarker/Downloads/OBS_audio.mp3"
f = open(file_path, "rb")
Prompt="This is a song. Transcribe both lyrics and non-sence (Woo Woo) words in the song."
transcript = Whisper_Call(f, Prompt)

##TODO: 
 - [ ] Add calls to local whisper.cpp
 - [ ] Add Diarization https://github.com/lablab-ai/Whisper-transcription_and_diarization-speaker-identification-
 - [ ] add conversions for mp4, mpeg, mpga, m4a, and webm (obsolete?)
 - [ ] test file formats
"""

Whisper_Max_Chunk_Size__MB = 25

def install_dependency(package_name):
    try:
        importlib.import_module(package_name)
    except ImportError:
        print(f"{package_name} not found. Installing it...")
        subprocess.check_call(["pip","install",package_name])
        print(f"end installation effort for {package_name} package")

def __Transcribe(input_file_path:str, output_file_path:str, Prompt:str, Temp:float=0.,Language:str='en',True_fileversion__False_strversion = False) -> str:
    #TODO vett file paths
    WC = Whisper_Controler()
    WC.Set_Temp(Temp)
    WC.Set_Instruction(Prompt)
    WC.Set_Language(Language)
    WC.Set_autodisable(True)
    if True_fileversion__False_strversion:
        WC.Transcribe_loop_to_file(input_file_path, output_file_path)
    else:
        return WC.Transcribe_to_str(input_file_path) 

def Transcribe_to_str(input_file_path:str, Prompt:str, Temp:float=0.,Language:str='en') -> str:
    return __Transcribe(input_file_path, "", Prompt, Temp,Language,False) 

def Transcribe_to_file(input_file_path:str, output_file_path:str, Prompt:str, Temp:float=0.,Language:str='en')->None:
    __Transcribe(input_file_path, output_file_path, Prompt, Temp,Language,True) 

def Transcribe_to_file_autoNameOutput(input_file_path:str, Prompt:str,Temp:float=0.,Language:str='en')->None:
    #Writes a transcript file to the same filepath as the input, but as a txt file.
    output_file_path= replace_extension(input_file_path)
    Transcribe_to_file(input_file_path, output_file_path, Prompt, Temp,Language)

def get_Price(audio_length_ms):
    #The price in dollars of transcribing this audio
    return Whisper_Controler().get_Price(audio_length_ms)
    #audio_length_s = round(audio_length_ms/1000.,0)
    #return 0.006*audio_length_s  #see https://openai.com/pricing

def is_openAI_audio_format(Format:str)->bool:
    ok_formats = ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]
    return Format.lower() in ok_formats

def is_pydub_audio_format(Format:str)->bool:
    ok_formats = [ "mp3", "wav", "ogg", "flac", "aac", "wma", "aiff","raw","pcm","au"]
        #[".mp3", ".wav", ".au", ".ogg", flac]
        #from source code: wav, raw, pcm, and possibly everything accepted by ffmpeg/avconv
    return (Format.lower() in ok_formats) or is_FFMPEG_audio_format(Format) 
    #it looks like pydub.AudioSegment.from_file takes raw, pcm, and everything that FFMPEG takes. Not sure though
    # see https://github.com/jiaaro/pydub/blob/master/pydub/audio_segment.py

def is_FFMPEG_audio_format(Format:str)->bool:
    #generated from $ ffmpeg -formats
    ok_formats = ["3dostr","3g2","3gp","4xm","a64","aa","aac","ac3","acm","act","adf","adp","ads","adts","adx","aea","afc","aiff","aix","alaw","alias_pix","alsa","amr","amrnb","amrwb","anm","apc","ape","apng","aptx","aptx_hd","aqtitle","asf","asf_o","asf_stream","ass","ast","au","avi","avisynth","avm2","avr","avs","avs2","bethsoftvid","bfi","bfstm","bin","bink","bit","bmp_pipe","bmv","boa","brender_pix","brstm","c93","caca","caf","cavsvideo","cdg","cdxl","chromaprint","cine","codec2","codec2raw","concat","crc","dash","data","daud","dcstr","dds_pipe","dfa","dhav","dirac","dnxhd","dpx_pipe","dsf","dsicin","dss","dts","dtshd","dv","dvbsub","dvbtxt","dvd","dxa","ea","ea_cdata","eac3","epaf","exr_pipe","f32be","f32le","f4v","f64be","f64le","fbdev","ffmetadata","fifo","fifo_test","film_cpk","filmstrip","fits","flac","flic","flv","framecrc","framehash","framemd5","frm","fsb","g722","g723_1","g726","g726le","g729","gdv","genh","gif","gif_pipe","gsm","gxf","h261","h263","h264","hash","hcom","hds","hevc","hls","hnm","ico","idcin","idf","iec61883","iff","ifv","ilbc","image2","image2pipe","ingenient","ipmovie","ipod","ircam","ismv","iss","iv8","ivf","ivr","j2k_pipe","jack","jacosub","jpeg_pipe","jpegls_pipe","jv","kmsgrab","kux","latm","lavfi","libcdio","libdc1394","libgme","libopenmpt","live_flv","lmlm4","loas","lrc","lvf","lxf","m4v","matroska","matroska","webm","md5","mgsts","microdvd","mjpeg","mjpeg_2000","mkvtimestamp_v2","mlp","mlv","mm","mmf","mov","mov","mp4","m4a","3gp","3g2","mj2","mp2","mp3","mp4","mpc","mpc8","mpeg","mpeg1video","mpeg2video","mpegts","mpegtsraw","mpegvideo","mpjpeg","mpl2","mpsub","msf","msnwctcp","mtaf","mtv","mulaw","musx","mv","mvi","mxf","mxf_d10","mxf_opatom","mxg","nc","nistsphere","nsp","nsv","null","nut","nuv","oga","ogg","ogv","oma","openal","opengl","opus","oss","paf","pam_pipe","pbm_pipe","pcx_pipe","pgm_pipe","pgmyuv_pipe","pictor_pipe","pjs","pmp","png_pipe","ppm_pipe","psd_pipe","psp","psxstr","pulse","pva","pvf","qcp","qdraw_pipe","r3d","rawvideo","realtext","redspark","rl2","rm","roq","rpl","rsd","rso","rtp","rtp_mpegts","rtsp","s16be","s16le","s24be","s24le","s32be","s32le","s337m","s8","sami","sap","sbc","sbg","scc","sdl","sdl2","sdp","sdr2","sds","sdx","segment","ser","sgi_pipe","shn","siff","singlejpeg","sln","smjpeg","smk","smoothstreaming","smush","sndio","sol","sox","spdif","spx","srt","stl","stream_segment","ssegment","subviewer","subviewer1","sunrast_pipe","sup","svag","svcd","svg_pipe","swf","tak","tedcaptions","tee","thp","tiertexseq","tiff_pipe","tmv","truehd","tta","tty","txd","ty","u16be","u16le","u24be","u24le","u32be","u32le","u8","uncodedframecrc","v210","v210x","vag","vc1","vc1test","vcd","vidc","video4linux2","v4l2","vividas","vivo","vmd","vob","vobsub","voc","vpk","vplayer","vqf","w64","wav","wc3movie","webm","webm_chunk","webm_dash_manifest","webp","webp_pipe","webvtt","wsaud","wsd","wsvqa","wtv","wv","wve","x11grab","xa","xbin","xmv","xpm_pipe","xv","xvag","xwd_pipe","xwma","yop","yuv4mpegpipe"]
    return Format.lower() in ok_formats
#currently mp4, mpeg, mpga, m4a, and webm files cannot be looped over since they are not pydub formats 
#TODO add conversion

def Vet_FileType(Format:str, file_size__MB:float):
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

for mp4 inputs, and m4a:
from moviepy.editor import AudioFileClip
video_clip = AudioFileClip(input_mp4_file)
audio_segment = AudioSegment.from_file(video_clip)
audio_segment.export(output_mp3_file, format="mp3")

should be able to use with just AudioClip with mp4, mpg, mpga (both are mpeg)
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

    Based on whisperCPP, we can guess at the other possible reponce formats: csv, vtt, srt, lrc 
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
    #The website sucks, go directly to the code: https://github.com/openai/whisper/blob/0a60fcaa9b86748389a656aa013c416030287d47/whisper/transcribe.py#L36
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

class Whisper_Controler:
    def __init__(self):
        self.disable_openAI_calls:bool = False #ok
        self.autodisable = True #automatically disable expensive API calls
        self.is_test_mode:bool = False #ok
        self.echo:bool = False
        self.verbosity=Verb.normal
        self.test_mode_max_chunks = 999 #ok
        self.input_safety_margin = 0.8 
        self.Instructions = "Transcribe this discussion" #Initial prompt for the transcription
        self.Language = 'en'
        self.Temp = 0
        self.price = 0.006 #price in USD per min of audio transcribed, rounded to nearest second
    def Set_Echo(self,echo:bool) -> None:
        self.echo = echo
    def Set_disable_openAI_calls(self,disable:bool) -> None:
        self.disable_openAI_calls = disable
    def Set_autodisable(self, autodisable: bool = True)->None:
        self.autodisable = autodisable
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
    def get_Price(self,audio_length_ms):
        #The price in dollars of transcribing this audio
        audio_length_s = round(audio_length_ms/1000.,0)
        audio_length_min = audio_length_s/60.
        return self.price*audio_length_min #see https://openai.com/pricing
    def Discuss_Pricing_with_User(self, audio_length_ms:int, enable_user_prompt:bool = True) -> None:
        est_cost__USD = self.get_Price(audio_length_ms)
        if self.verbosity >= Verb.birthDeathMarriage or (est_cost__USD > 0.1 and self.verbosity != Verb.silent):
            print(f"Expected cost of this transcription: ${round(get_Price(audio_length_ms),3):.3f}") 
            if enable_user_prompt and est_cost__USD > 0.5 and self.verbosity != Verb.silent:
                answer = input("Would you like to continue? (y/n): ")
                if not (answer.lower() == 'y' or answer.lower == 'yes'):
                    print("Disabling OpenAI API calls")
                    self.Set_disable_openAI_calls(True)
            elif self.autodisable and not enable_user_prompt and est_cost__USD > 5:
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
    def Set_Input_Safety_Margins(self, input_safety_margin:float ) -> None:
        self.input_safety_margin = input_safety_margin
    def whisper_call(self,binary_file_handle):
        transcript = ""
        if not self.disable_openAI_calls:
            transcript = Whisper_Call(binary_file_handle, self.Instructions, self.Temp, "text", self.Language)
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

    def Transcribe_loop_to_file(self, input_file_path:str, output_file_path:str)->None:
        self.__Transcribe_loop(input_file_path, output_file_path, True)

    def Transcribe_to_str(self, input_file_path:str) -> str:
        return self.__Transcribe_loop(input_file_path, "", False)

    def __Transcribe_loop(self, input_file_path:str, output_file_path:str="", True_fileversion__False_strversion = False)->None:
        global Whisper_Max_Chunk_Size__MB
        if not os.path.exists(input_file_path):
            print(f"Error: file not found: {input_file_path}")
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
            self.Discuss_Pricing_with_User(audio_length_ms, self.verbosity > Verb.script)
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
                Text = self.whisper_call(audio)
                if True_fileversion__False_strversion:
                    with open(output_file_path,'a') as fp:
                        fp.write(Text + '\n')
                else:
                    text.append(Text)
                    #text.append(self.whisper_call(segment_v2))
        if self.verbosity >= Verb.birthDeathMarriage:
            print("done whispering")
        if not True_fileversion__False_strversion:
            return '\n'.join(text)

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


class whisper_models(IntEnum):
    base = auto()
    medium = auto()
    large = auto()

class output_fmt(IntEnum):
    txt = auto()
    vtt = auto()
    srt = auto()
    lrc = auto()
    wts = auto()
    csv = auto()
    json = auto()
  
#Call to local whisperCPP:
def whisper_local_call(audio_file_path:str, transcript_file_path:str, prompt:str = "", diarizaiton: bool = False, model:whisper_model=whisper_model.base, output_type:output_fmt = output_fmt.txt) -> None:

    model_str = {whisper_models.base:"models/ggml-base.en.bin",
            whisper_models.medium:"models/ggml-large.bin",
            whisper_models.large:"models/ggml-medium.bin"}[model]

    output_cmdstr = { output_fmt.txt:"-otxt", output_fmt.vtt:"-ovtt", output_fmt.srt:"-osrt", output_fmt.lrc:"-olrc", output_fmt.wts:"-owts", output_fmt.csv:"-ocsv", output_fmt.json:"-oj"}[output_type]

    output_ext = { output_fmt.txt:".txt", output_fmt.vtt:".vtt", output_fmt.srt:".srt", output_fmt.lrc:".lrc", output_fmt.wts:".wts", output_fmt.csv:".csv", output_fmt.json:".json"}[output_type]
    wave_file_path = parse_fname(audio_file_path)[0] + ".wav"

    #convert to wav
    ffmpg_cmd:str = ""
    if diarizaiton:
        ffmpg_cmd= f"ffmpeg -loglevel -0 -y -i {audio_file_path} -ar 16000 -ac 2 -c:a pcm_s16le {wave_file_path}"
    else:
        ffmpg_cmd = f"ffmpeg -loglevel -0 -y -i {audio_file_path} -ar 16000 -ac 1 -c:a pcm_s16le {wave_file_path}"
    print(f"ffmpg cmd: {ffmpg_cmd}")
    os.system(ffmpg_cmd)

    #run whispercpp
    whisper_cmd:str = f"{whisperCPP_dir}/main -f {wave_file_path} -m {model_str } {output_cmdstr}"
    if diarizaiton:
        whisper_cmd += ' -di'
    if not prompt == '':
        whisper_cmd += f'--prompt "{prompt}"'
    print(f"whisper cmd: {whisper_cmd}")
    os.system(whisper_cmd)
   
    #move the output file
    whisper_output_filepath = wave_file_path + output_ext 
    mv_cmd = f"mv {whisper_output_filepath} {transcript_file_path}"
    print(f"move cmd: {mv_cmd}")
    os.system(mv_cmd )
   
    #clean up by removing the wave file
    rm_cmd = f"\\rm {wave_file_path}"
    print(f"rm wave file: {rm_cmd}")
    os.system(rm_cmd)

"""
options that seem useful:
  -t N,      --threads N         [4      ] number of threads to use during computation
  -p N,      --processors N      [1      ] number of processors to use during computation #Andrei7 has 10
  -d  N,     --duration N        [0      ] duration of audio to process in milliseconds -- useful limiter
  -tr,       --translate         [false  ] translate from source language to english
  -di,       --diarize           [false  ] stereo audio diarization
  -otxt,     --output-txt        [false  ] output result in a text file
  -ovtt,     --output-vtt        [false  ] output result in a vtt file
  -olrc,     --output-lrc        [false  ] output result in a lrc file
  -ocsv,     --output-csv        [false  ] output result in a CSV file
  -oj,       --output-json       [false  ] output result in a JSON file
  -nt,       --no-timestamps     [true   ] do not print timestamps
  -l LANG,   --language LANG     [en     ] spoken language ('auto' for auto-detect)
  -dl,       --detect-language   [false  ] exit after automatically detecting language
             --prompt PROMPT     [       ] initial prompt
  -m FNAME,  --model FNAME       [models/ggml-base.en.bin] model path
  -f FNAME,  --file FNAME        [       ] input WAV file path
all options:
  -t N,      --threads N         [4      ] number of threads to use during computation
  -p N,      --processors N      [1      ] number of processors to use during computation #Andrei7 has 10
  -ot N,     --offset-t N        [0      ] time offset in milliseconds
  -on N,     --offset-n N        [0      ] segment index offset
  -d  N,     --duration N        [0      ] duration of audio to process in milliseconds -- useful limiter
  -mc N,     --max-context N     [-1     ] maximum number of text context tokens to store
  -ml N,     --max-len N         [0      ] maximum segment length in characters
  -sow,      --split-on-word     [false  ] split on word rather than on token
  -bo N,     --best-of N         [2      ] number of best candidates to keep
  -bs N,     --beam-size N       [-1     ] beam size for beam search
  -wt N,     --word-thold N      [0.01   ] word timestamp probability threshold
  -et N,     --entropy-thold N   [2.40   ] entropy threshold for decoder fail
  -lpt N,    --logprob-thold N   [-1.00  ] log probability threshold for decoder fail
  -su,       --speed-up          [false  ] speed up audio by x2 (reduced accuracy)
  -tr,       --translate         [false  ] translate from source language to english
  -di,       --diarize           [false  ] stereo audio diarization
  -nf,       --no-fallback       [false  ] do not use temperature fallback while decoding
  -otxt,     --output-txt        [false  ] output result in a text file
  -ovtt,     --output-vtt        [false  ] output result in a vtt file
  -osrt,     --output-srt        [false  ] output result in a srt file
  -olrc,     --output-lrc        [false  ] output result in a lrc file
  -owts,     --output-words      [false  ] output script for generating karaoke video
  -fp,       --font-path         [/System/Library/Fonts/Supplemental/Courier New Bold.ttf] path to a monospace font for karaoke video
  -ocsv,     --output-csv        [false  ] output result in a CSV file
  -oj,       --output-json       [false  ] output result in a JSON file
  -of FNAME, --output-file FNAME [       ] output file path (without file extension)
  -ps,       --print-special     [false  ] print special tokens
  -pc,       --print-colors      [false  ] print colors
  -pp,       --print-progress    [false  ] print progress
  -nt,       --no-timestamps     [true   ] do not print timestamps
  -l LANG,   --language LANG     [en     ] spoken language ('auto' for auto-detect)
  -dl,       --detect-language   [false  ] exit after automatically detecting language
             --prompt PROMPT     [       ] initial prompt
  -m FNAME,  --model FNAME       [models/ggml-base.en.bin] model path
  -f FNAME,  --file FNAME        [       ] input WAV file path
Models:
models/for-tests-ggml-base.bin
models/for-tests-ggml-base.en.bin
models/for-tests-ggml-large.bin
models/for-tests-ggml-medium.bin
models/for-tests-ggml-medium.en.bin
models/for-tests-ggml-small.bin
models/for-tests-ggml-small.en.bin
models/for-tests-ggml-tiny.bin
models/for-tests-ggml-tiny.en.bin
models/ggml-base.bin
models/ggml-base.en.bin
models/ggml-large.bin
models/ggml-medium.bin
CSV:
start,end,text
0,1280," It's good to see you."
LRC:
[by:whisper.cpp]
[00:00.00] It's good to see you.
VTT:
WEBVTT

00:00:00.000 --> 00:00:01.280
 It's good to see you.
LRT:
1
00:00:00,000 --> 00:00:01,280
 It's good to see you.
  """
#no need to chunk with whispercpp! It can take long audio. But it returns nothing before hand.
