import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'modules')))

from tts import synthesize_speech_with_srt

if __name__ == "__main__":
    with open("bin/test/input/test_text.txt", "r") as f:
        text = f.read()
    mp3_output_filepath = "bin/test/output/tts_test_output.mp3"        
    srt_output_filepath = "bin/test/output/srt_test_output.srt"
    synthesize_speech_with_srt(text, mp3_output_filepath, srt_output_filepath)