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

    voice_names = [voice["name"] for voice in get_voices()]
    if not voice in voice_names:
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

    # Generate and save the SRT file using srt library
    def save_srt_file(timestamps, filename):
        subtitles = []
        current_subtitle = ""
        current_start_time = None

        # Define Chinese punctuation
        chinese_punctuation = re.compile(r'[。！？；，、]')

        for i, entry in enumerate(timestamps):
            if current_start_time is None:
                current_start_time = timedelta(milliseconds=entry["start_time"])

            current_subtitle += entry["text"]

            if i + 1 < len(timestamps):
                next_start_time = timedelta(milliseconds=timestamps[i + 1]["start_time"])
                if chinese_punctuation.search(entry["text"]):
                    end_time = next_start_time
                    subtitle = srt.Subtitle(index=len(subtitles) + 1, start=current_start_time, end=end_time, content=current_subtitle.strip())
                    subtitles.append(subtitle)
                    current_subtitle = ""
                    current_start_time = None
            else:
                end_time = timedelta(milliseconds=entry["start_time"]) + timedelta(milliseconds=500)
                subtitle = srt.Subtitle(index=len(subtitles) + 1, start=current_start_time, end=end_time, content=current_subtitle.strip())
                subtitles.append(subtitle)

        srt_content = srt.compose(subtitles)
        with open(filename, "w", encoding="utf-8") as srt_file:
            srt_file.write(srt_content)

    # Save the SRT file
    save_srt_file(timestamps, srt_output_filepath)

    print("Speech synthesis complete!")
    print(f"Generated: {mp3_output_filepath} and {srt_output_filepath}")

