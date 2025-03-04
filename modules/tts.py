import azure.cognitiveservices.speech as speechsdk
import srt
from datetime import timedelta
import re
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

def get_voices():
    voices = [
        {"name": "zh-CN-YunxiaNeural", "description": "Male - Child"},
        {"name": "zh-CN-XiaoshuangNeural", "description": "Female - Child"},
        {"name": "zh-CN-YunxiNeural", "description": "Male - Young Adult"},
        {"name": "zh-CN-XiaoxiaoNeural", "description": "Female - Young Adult"},
        {"name": "zh-CN-YunjianNeural", "description": "Male - Adult"},
        {"name": "zh-CN-XiaorouNeural", "description": "Female - Adult"},
        {"name": "zh-CN-YunyeNeural", "description": "Male - Senior"},
        {"name": "zh-CN-XiaoqiuNeural", "description": "Female - Senior"},
    ]
    return voices

def synthesize_speech_with_srt(text, voice, mp3_output_filepath, srt_output_filepath):
    # Initialize speech configuration
    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    audio_config = speechsdk.audio.AudioOutputConfig(filename=mp3_output_filepath)

    # Set language and voice (Mandarin Chinese)
    speech_config.speech_synthesis_language = "zh-CN"

    voice_names = [v["name"] for v in get_voices()]
    if voice not in voice_names:
        raise ValueError(f"Voice '{voice}' not found. Available voices: {voice_names}")
    speech_config.speech_synthesis_voice_name = voice 

    # Create a speech synthesizer object
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    # Store timestamps
    timestamps = []

    # Word boundary callback function
    def word_boundary_callback(event):
        word_info = {
            "text": event.text,
            "start_time": event.audio_offset / 10_000,  # Convert ticks to milliseconds
        }
        timestamps.append(word_info)

    # Connect callback to event
    speech_synthesizer.synthesis_word_boundary.connect(word_boundary_callback)

    # Run speech synthesis
    result = speech_synthesizer.speak_text_async(text).get()



    def build_subtitle(timestamps, index):
        """takes a list of timestamps and returnes a single srt.Subtitle object that groups all the timestamps in the list"""
        subtitle_text = "".join([ts["text"] for ts in timestamps])
        start_time = timedelta(milliseconds=timestamps[0]["start_time"]) if timestamps else timedelta(0)
        end_time = timedelta(milliseconds=timestamps[-1]["start_time"] + 500) if timestamps else timedelta(500)
        return srt.Subtitle(
            index=index,
            start=start_time,
            end=end_time,
            content=subtitle_text.strip()
        )

    # Generate and save the SRT file using srt library
    def save_srt_file(timestamps, filename):
        chinese_punctuation = "，。！？、“”"

        subtitles = []
        curr_group = []

        subtitle_index = 1

        i = 0
        while i < len(timestamps):
            if timestamps[i]["text"] in chinese_punctuation:
                while (i+1 < len(timestamps)) and (timestamps[i+1]["text"] in chinese_punctuation):
                    curr_group.append(timestamps[i])
                    i += 1
                    if i == len(timestamps):
                        break
                curr_group.append(timestamps[i])
                subtitles.append(build_subtitle(curr_group, subtitle_index))
                subtitle_index += 1
                curr_group = []

            else:
                curr_group.append(timestamps[i])
            i += 1
                        
        # adjust improperly placed closing dialogue characters
        i = 1
        while i < len(subtitles):
            if subtitles[i].content[0] == "”":
                subtitles[i-1].content += "”"
                subtitles[i].content = subtitles[i].content[1:] 
            i += 1

        # strip subtitles
        for subtitle in subtitles:
            subtitle.content = subtitle.content.lstrip(" \t\n")
            print(subtitle.content)

        # write the subtitle content
        srt_content = srt.compose(subtitles)
        with open(filename, "w", encoding="utf-8") as srt_file:
            srt_file.write(srt_content)

    # Save the SRT file
    save_srt_file(timestamps, srt_output_filepath)

    print("Speech synthesis complete!")
    print(f"Generated: {mp3_output_filepath} and {srt_output_filepath}")

