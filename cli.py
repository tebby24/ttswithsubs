import os
import subprocess
import tempfile
from ttswithsubs import TTSWithSubsGenerator, VideoGenerator

def main():
    # Get the default editor from the environment or use 'nano'
    editor = os.getenv('EDITOR', 'nano')
    template = """# Title
Your title here

# Content
Your content here
"""
    # Create a temporary file for the user to edit
    with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(template.encode('utf-8'))
        temp_file.flush()
        subprocess.call([editor, temp_file_path])

    # Read the content from the temporary file
    with open(temp_file_path, 'r') as file:
        content = file.read()

    # Remove the temporary file
    os.remove(temp_file_path)

    # Split the content into title and text
    title, text = content.split("# Content\n", 1)
    title = title.replace("# Title\n", "").strip()
    text = text.strip()

    # Define the output directory based on the title
    output_dir = os.path.expanduser(f"~/Downloads/{title}")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Create an instance of the TTSWithSubsGenerator
    tts_generator = TTSWithSubsGenerator()
    
    # Get list of available voices
    voices = tts_generator.get_voices()

    # Prompt the user to choose a voice
    print("Please choose a voice:")
    for i, voice in enumerate(voices, 1):
        print(f"{i}. {voice['description']}")

    choice = int(input("Enter the number of your choice: "))
    voice = voices[choice - 1]['name']

    # Prompt the user for an image filepath
    image_filepath = input("Enter an image filepath (leave blank for no image): ")

    print("\nSynthesizing speech...")
    # Generate TTS and subtitles using the class instance
    mp3_output_filepath = f"{output_dir}/speech.mp3"
    srt_output_filepath = f"{output_dir}/transcript.srt"
    tts_generator.synthesize_speech_with_srt(text, voice, mp3_output_filepath, srt_output_filepath)

    if image_filepath:
        print("Generating video...")
        video_generator = VideoGenerator()
        video_generator.generate_video(image_filepath, mp3_output_filepath, f"{output_dir}/video.mp4")
        print(f"\nSpeech, subtitles, and video saved to: {output_dir}")
    else:
        print(f"\nSpeech and subtitles saved to: {output_dir}")

if __name__ == "__main__":
    main()