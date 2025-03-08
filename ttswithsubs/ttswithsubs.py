import azure.cognitiveservices.speech as speechsdk
import srt
from datetime import timedelta
import re
from dotenv import load_dotenv
import os
import requests
import json
import time
import uuid
import zipfile
import io
import tempfile
from moviepy import *

# Load environment variables from .env file
load_dotenv()

class TTSWithSubsGenerator:
    def __init__(self, azure_speech_key, azure_speech_region):
        """Initialize the TTS generator with Azure credentials from environment variables."""
        self.speech_key = azure_speech_key
        self.speech_region = azure_speech_region
        self.speech_endpoint = f"https://{self.speech_region}.api.cognitive.microsoft.com"
        self.api_version = "2024-04-01"
        
        if not self.speech_key or not self.speech_region:
            raise ValueError("Azure Speech credentials not found in environment variables")

    def get_voices(self):
        """Return a list of available voice options for Chinese."""
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

    def synthesize_speech_with_srt(self, text, voice, mp3_output_filepath, srt_output_filepath):
        """
        Generate speech from text and create a synchronized subtitle file.
        
        Args:
            text (str): The text to synthesize
            voice (str): The voice name to use
            mp3_output_filepath (str): Path to save the MP3 audio output
            srt_output_filepath (str): Path to save the SRT subtitle output
        """
        voice_names = [v["name"] for v in self.get_voices()]
        if voice not in voice_names:
            raise ValueError(f"Voice '{voice}' not found. Available voices: {voice_names}")

        # Create a unique job ID
        job_id = str(uuid.uuid4())
        
        # Create the batch synthesis request
        headers = {
            "Ocp-Apim-Subscription-Key": self.speech_key,
            "Content-Type": "application/json"
        }

        body = {
            "inputKind": "PlainText",
            "synthesisConfig": {
                "voice": voice,
            },
            "inputs": [
                {
                    "content": text
                },
            ],
            "properties": {
                "outputFormat": "audio-16khz-32kbitrate-mono-mp3",
                "wordBoundaryEnabled": True
            }
        }

        # Submit the synthesis job
        url = f"{self.speech_endpoint}/texttospeech/batchsyntheses/{job_id}?api-version={self.api_version}"
        print(f"Starting batch synthesis job...")
        
        response = requests.put(url, data=json.dumps(body), headers=headers)
        if not response.ok:
            print(f"Error: {response.status_code} - {response.text}")
            response.raise_for_status()
        
        print(f"Job created successfully")

        # Poll for the batch synthesis result
        status_url = f"{self.speech_endpoint}/texttospeech/batchsyntheses/{job_id}?api-version={self.api_version}"
        print(f"Waiting for synthesis to complete...")
        
        while True:
            response = requests.get(status_url, headers=headers)
            if not response.ok:
                response.raise_for_status()
            
            result = response.json()
            status = result.get("status")
            
            if status == "Succeeded":
                break
            elif status == "Failed":
                error_message = result.get("errors", ["Unknown error"])[0]
                raise Exception(f"Batch synthesis failed: {error_message}")
            
            time.sleep(10)

        # Download the synthesized audio
        outputs = result.get("outputs", {})
        if not outputs:
            raise Exception("No outputs found in the response")
        
        # Handle the ZIP file
        zip_url = outputs.get("result")
        if not zip_url:
            raise Exception("Result ZIP URL not found in the response")
        
        print(f"Downloading results...")
        zip_response = requests.get(zip_url)
        if not zip_response.ok:
            raise Exception(f"Failed to download ZIP: {zip_response.status_code}")
        
        self._process_zip_response(zip_response, text, mp3_output_filepath, srt_output_filepath)

        print("Speech synthesis complete!")
        print(f"Generated: {mp3_output_filepath} and {srt_output_filepath}")

    def _process_zip_response(self, zip_response, text, mp3_output_filepath, srt_output_filepath):
        """Process the ZIP file response from the TTS service."""
        # Create a temporary directory to extract the ZIP
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "results.zip")
            
            # Save the ZIP file
            with open(zip_path, "wb") as zip_file:
                zip_file.write(zip_response.content)
            
            # Extract the ZIP file
            try:
                with zipfile.ZipFile(zip_path, "r") as z:
                    # Find the audio file and word boundary file
                    audio_file_name = None
                    word_boundary_file_name = None
                    
                    for file_name in z.namelist():
                        if file_name.endswith(".mp3"):
                            audio_file_name = file_name
                        elif file_name.endswith(".word.json"):
                            word_boundary_file_name = file_name
                    
                    if not audio_file_name:
                        raise Exception("Audio file not found in the ZIP")
                    
                    # Extract the audio file and save it to the output path
                    with open(mp3_output_filepath, "wb") as f:
                        f.write(z.read(audio_file_name))
                    
                    # Process word boundaries if available
                    if word_boundary_file_name:
                        word_boundaries = json.loads(z.read(word_boundary_file_name).decode("utf-8"))
                        
                        # Process word boundaries to generate SRT file
                        timestamps = []
                        for item in word_boundaries:
                            if "Text" in item and "AudioOffset" in item:
                                word_info = {
                                    "text": item.get("Text", ""),
                                    "start_time": item.get("AudioOffset")  # Already in milliseconds
                                }
                                timestamps.append(word_info)
                        
                        self._save_srt_file(timestamps, srt_output_filepath)
                    else:
                        print("Warning: Word boundaries not available. Creating default subtitle.")
                        # Create a simple SRT with just the entire text
                        with open(srt_output_filepath, "w", encoding="utf-8") as srt_file:
                            srt_file.write("1\n00:00:00,000 --> 00:05:00,000\n" + text)
            except zipfile.BadZipFile as e:
                print(f"Error: The downloaded file is not a valid ZIP file: {e}")
                # Try to save the raw content as MP3 directly
                with open(mp3_output_filepath, "wb") as f:
                    f.write(zip_response.content)
                
                # Create a simple SRT with just the entire text
                with open(srt_output_filepath, "w", encoding="utf-8") as srt_file:
                    srt_file.write("1\n00:00:00,000 --> 00:05:00,000\n" + text)

    def _build_subtitle(self, timestamps, index):
        """
        Takes a list of timestamps and returns a single srt.Subtitle object 
        that groups all the timestamps in the list.
        """
        subtitle_text = "".join([ts["text"] for ts in timestamps])
        start_time = timedelta(milliseconds=timestamps[0]["start_time"]) if timestamps else timedelta(0)
        end_time = timedelta(milliseconds=timestamps[-1]["start_time"] + 500) if timestamps else timedelta(500)
        return srt.Subtitle(
            index=index,
            start=start_time,
            end=end_time,
            content=subtitle_text.strip()
        )

    def _save_srt_file(self, timestamps, filename):
        """
        Generate an SRT subtitle file from word timestamps.
        
        This groups words into subtitle entries based on punctuation.
        """
        chinese_punctuation = "，。！？、"""

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
                subtitles.append(self._build_subtitle(curr_group, subtitle_index))
                subtitle_index += 1
                curr_group = []
            else:
                curr_group.append(timestamps[i])
            i += 1

        # adjust improperly placed closing dialogue characters
        i = 1
        while i < len(subtitles):
            if subtitles[i].content[0] == '"':
                subtitles[i-1].content += '"'
                subtitles[i].content = subtitles[i].content[1:]
            i += 1

        # strip subtitles
        for subtitle in subtitles:
            subtitle.content = subtitle.content.lstrip(" \t\n")

        # fix overlapping subtitles
        i = 0
        while i < len(subtitles) - 1:
            if subtitles[i].end > subtitles[i+1].start:
                subtitles[i].end = subtitles[i+1].start
            i += 1

        # write the subtitle content
        srt_content = srt.compose(subtitles)
        with open(filename, "w", encoding="utf-8") as srt_file:
            srt_file.write(srt_content)

class VideoGenerator:
    def generate_video(image_filepath, mp3_filepath, mp4_output_filepath):
        audio = AudioFileClip(mp3_filepath)
        clip = ImageClip(image_filepath).with_duration(audio.duration)
        clip = clip.with_audio(audio)
        clip.write_videofile(mp4_output_filepath, fps=24)