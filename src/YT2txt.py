from pytube import YouTube
import re
import whisper_utils as wu

def Title2Filename(title:str):
    pattern = r'[^A-Za-z0-9\-_]+'
    cleaned_string = re.sub(pattern, '', input_string).strip()
    return cleaned_string.replace(' ','_')

vidURL = "https://www.youtube.com/watch?v=ZmKNtH5J01A&list=PLPY6wPeme2Tvje6RxVezYMmB5CAsyPb86&index=1"
prompt = "Transcribe this conversation"
Temp = 0.

yt = YouTube(vidURL,
        use_oauth=True,
        allow_oauth_cache=True) 
#YouTube object documentation: https://pytube.io/en/latest/api.html?highlight=likes#youtube-object


title_str = yt.title
audio_filename_prefix = Title2Filename(title_str) 
audio_filename_extension = ".webm"

#print("mp4 streams")
#print(yt.streams.filter(file_extension='mp4'))
    #stream object documentation: https://pytube.io/en/latest/api.html?highlight=likes#stream-object
#print("audio streams")
#print(yt.streams.filter(only_audio=True))
#audio_streams = yt.streams.filter(only_audio=True)
#print(audio_streams.filter( abr="128kbps"))

chosen_stream = yt.streams.get_audio_only(subtype = 'webm')
if chosen_stream is None:
    chosen_stream = yt.streams.get_audio_only()
    print("mp4 mode")#debug
    audio_filename_extension = ".mp4"
if not (chosen_stream is None):
    audio_filename = audio_filename_prefix+audio_filename_extension

    #download the audio
    print(f"Downloading audio for: {title_str}")
    chosen_stream.download(filename=audio_filename, skip_existing=True)

    #call whisper
    wu.Transcribe_to_file_autoNameOutput(audio_filename, prompt, Temp)

    #delete audio file.
    rm_cmd = "rm "+audio_filename 
    print(rm_cmd)
    os.system(rm_cmd) 
else:
    print("No suitable audio stream found. Available streams:")
    audio_streams = yt.streams.filter(only_audio=True)
    for stream in audio_streams:
        print(stream)


#ok, this sucks. I need Diarization
#see here: https://github.com/lablab-ai/Whisper-transcription_and_diarization-speaker-identification-
