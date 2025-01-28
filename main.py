import os
import asyncio
import edge_tts
import srt
import subprocess
import tempfile
import srt
from moviepy import *

def process_word_srt(word_srt_content):
    """
    Process a word-by-word timestamped SRT file and generate grouped subtitles based on natural pauses.
    """
    # Parse the word-by-word SRT content into a list of Subtitle objects
    srt_entries = list(srt.parse(word_srt_content))

    # Define a threshold for detecting pauses
    from datetime import timedelta
    PAUSE_THRESHOLD = timedelta(milliseconds=50)
    
    # Initialize variables for grouping words into lines based on pauses
    grouped_subtitles = []
    current_group = []
    current_start_time = None

    for i, entry in enumerate(srt_entries):
        # Start a new group if the current group is empty
        if not current_group:
            current_group.append(entry.content)
            current_start_time = entry.start
        else:
            # Check for a pause between the current and previous word
            if entry.start - srt_entries[i-1].end > PAUSE_THRESHOLD:
                # Finalize the current group and start a new one
                grouped_subtitles.append({
                    "content": "".join(current_group),  # Concatenate words without spaces
                    "start": current_start_time,
                    "end": srt_entries[i-1].end
                })
                # Start a new group with the current word
                current_group = [entry.content]
                current_start_time = entry.start
            else:
                # Add the current word to the existing group
                current_group.append(entry.content)

    # Add the last group after the loop ends
    if current_group:
        grouped_subtitles.append({
            "content": "".join(current_group),  # Concatenate words without spaces
            "start": current_start_time,
            "end": srt_entries[-1].end
        })

    return grouped_subtitles

def generate_srt_from_groups(grouped_subtitles):
    """
    Generate an SRT file from grouped subtitle data.
    """
    # Create SRT entries from the grouped subtitles
    srt_entries = []
    for i, group in enumerate(grouped_subtitles, start=1):
        entry = srt.Subtitle(
            index=i,
            start=group["start"],
            end=group["end"],
            content=group["content"]
        )
        srt_entries.append(entry)

    # Compose and return the final SRT content
    return srt.compose(srt_entries)


async def generate_tts(text, voice, output_dir) -> None:
    """Generate TTS audio and subtitles from text using edge_tts"""
    communicate = edge_tts.Communicate(text, voice)
    submaker = edge_tts.SubMaker()

    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Generate the audio and word-by-word SRT
    with open(f"{output_dir}/speech.mp3", "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)

    # Get the word-by-word SRT content
    word_srt = submaker.get_srt()

    # Convert the word-by-word SRT to grouped subtitles
    grouped_subtitles = process_word_srt(word_srt)
    final_srt_content = generate_srt_from_groups(grouped_subtitles)

    # Write the final grouped subtitles to an SRT file
    with open(f"{output_dir}/transcript.srt", "w", encoding="utf-8") as file:
        file.write(final_srt_content)

def generate_video(image_filepath, output_dir):
    audio = AudioFileClip(f"{output_dir}/speech.mp3")
    clip = ImageClip(image_filepath).with_duration(audio.duration)
    clip = clip.with_audio(audio)
    clip.write_videofile(f"{output_dir}/video.mp4", fps=24)


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
    
    # List of available voices
    voices = (
        ("zh-CN-XiaoxiaoNeural", "young adult woman"),
        ("zh-CN-XiaoyiNeural", "teen girl"),
        ("zh-CN-YunjianNeural", "adult male (passionate)"),
        ("zh-CN-YunxiNeural", "teen boy"),
        ("zh-CN-YunxiaNeural", "child boy"),
        ("zh-CN-YunyangNeural", "adult male (news)"),
    ) 

    # Prompt the user to choose a voice
    print("Please choose a voice:")
    for i, (voice, description) in enumerate(voices, 1):
        print(f"{i}. {description}")

    choice = int(input("Enter the number of your choice: "))
    voice = voices[choice - 1][0]

    # Prompt the user for a image filepath
    image_filepath = input("Enter an image filepath (leave blank for no image): ")

    print("\nSynthasizing speech...")
    # Generate TTS and subtitles
    asyncio.run(generate_tts(text, voice, output_dir))

    if(image_filepath):
        print("Generating video...")
        generate_video(image_filepath, output_dir)
        print(f"\nSpeech, subtitles, and video saved to: {output_dir}")
    else:
        print(f"\nSpeech and subtitles saved to: {output_dir}")


def test():
    # Sample text for testing
    text = """
中国，传统观念指位于天下正中的国家。原指包括河南省及附近的黄河中下游流域地区。历代王朝政权透过与周边各政权的交流与征战，中国的疆域版图几经扩张与缩减，目前扩及黑龙江流域、塞北、西域、青藏高原及南海诸岛等地。现今，国际上广泛承认代表“中国”的政权是中华人民共和国。
"""
    voice = "zh-CN-XiaoxiaoNeural"
    image_filepath = "test/Mao_Proclaiming_New_China.jpeg"
    output_dir = os.path.expanduser("test/output")
    asyncio.run(generate_tts(text, voice, output_dir))
    generate_video(image_filepath, output_dir)


if __name__ == "__main__":
    main()