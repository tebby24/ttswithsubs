import os
import asyncio
import edge_tts
import srt
import re
import subprocess
import tempfile

import logging
# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for detailed logs; change to INFO or WARNING for less verbosity
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_chunks_from_text(text):
    """
    Split the text into chunks by relevant Chinese punctuation and preserve punctuation.
    """
    # List of Chinese punctuation to split the text on
    punctuation_pattern = r'[，。？！？；：、“”‘’（）【】《》〈〉、……]'
    
    # Use regex to split the text, keeping the punctuation in the result
    chunks = re.split(f'({punctuation_pattern})', text)
    logger.debug(f"Split input text into base chunks: {chunks}")
    
    # Combine characters and punctuation into meaningful chunks
    result = []
    for i in range(0, len(chunks) - 1, 2):
        chunk = chunks[i] + (chunks[i + 1] if i + 1 < len(chunks) else "")
        result.append(chunk.strip())
    
    logger.debug(f"Final processed chunks: {result}")
    return result


def align_chunks_to_timestamps(chunks, srt_entries):
    """
    Align chunks to their respective start and end timestamps.
    """
    result = []
    current_word_index = 0
    entry_count = len(srt_entries)

    logger.debug(f"Number of chunks: {len(chunks)}")
    logger.debug(f"Number of SRT entries: {entry_count}")
    
    for i, chunk in enumerate(chunks):
        # Preprocess chunk to remove punctuation for matching
        clean_chunk = re.sub(r'[，。？！？；：、“”‘’（）【】《》〈〉、……]', '', chunk)

        # Extract words in the chunk
        words_in_chunk = list(clean_chunk)  # Characters for comparison
        words_matched = []

        start_time = None
        end_time = None

        # Match words in the chunk to SRT entries
        while current_word_index < entry_count and words_in_chunk:
            # Get next SRT entry
            srt_word = srt_entries[current_word_index].content

            # Match the SRT entry content with the chunk's content
            if clean_chunk.startswith(srt_word):
                if not start_time:  # Set the start time of the chunk
                    start_time = srt_entries[current_word_index].start

                # Reduce the chunk's content as words are matched
                clean_chunk = clean_chunk[len(srt_word):]
                words_matched.append(srt_word)

                # Set the end time to the current word
                end_time = srt_entries[current_word_index].end

                # Increment the current word index
                current_word_index += 1
            else:
                break

        # Ensure all words in the chunk are matched
        if clean_chunk:
            logger.error(f"Unmatched text in chunk: {chunk}")
            raise ValueError(f"Unable to fully match the chunk '{chunk}' with word SRT entries.")

        # Add the chunk with timestamps
        result.append((chunk, start_time, end_time))
        logger.debug(f"Chunk '{chunk}' aligned to start: {start_time}, end: {end_time}")
    
    return result


def convert_word_srt_to_punctuated_srt(input_text, word_srt_content):
    """
    Convert word timestamped SRT to punctuation-aligned SRT.
    """
    # Parse the word timestamped SRT
    srt_entries = list(srt.parse(word_srt_content))

    # Get chunks of the text based on punctuation
    chunks = get_chunks_from_text(input_text)

    # Align chunks to timestamps
    chunks_with_timestamps = align_chunks_to_timestamps(chunks, srt_entries)

    # Create new SRT entries with the aligned chunks and timestamps
    punctuated_srt_entries = []
    for i, (chunk, start_time, end_time) in enumerate(chunks_with_timestamps, start=1):
        entry = srt.Subtitle(index=i, start=start_time, end=end_time, content=chunk)
        punctuated_srt_entries.append(entry)

    # Generate the new SRT content
    punctuated_srt = srt.compose(punctuated_srt_entries)
    return punctuated_srt


async def generate_tts(text, voice, output_dir) -> None:
    """Generate TTS and subtitles from text using edge_tts"""
    communicate = edge_tts.Communicate(text, voice)
    submaker = edge_tts.SubMaker()

    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Generate the audio and word SRT
    with open(f"{output_dir}/speech.mp3", "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)

    # Write the word SRT file for debugging
    word_srt = submaker.get_srt()
    logger.debug(f"Generated word SRT: \n{word_srt}")
    with open(f"{output_dir}/word_transcript.srt", "w", encoding="utf-8") as file:
        file.write(word_srt)

    # Convert word SRT to punctuated SRT
    try:
        punctuated_srt = convert_word_srt_to_punctuated_srt(text, word_srt)
        logger.debug(f"Generated punctuated SRT: \n{punctuated_srt}")
    except Exception as e:
        logger.error("An error occurred during SRT conversion", exc_info=True)
        raise

    # Write the final punctuated SRT file
    with open(f"{output_dir}/transcript.srt", "w", encoding="utf-8") as file:
        file.write(punctuated_srt)


if __name__ == "__main__":
    editor = os.getenv('EDITOR', 'vi')
    template = """# Title
Your title here

# Content
Your content here
"""
    with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(template.encode('utf-8'))
        temp_file.flush()
        subprocess.call([editor, temp_file_path])

    with open(temp_file_path, 'r') as file:
        content = file.read()

    os.remove(temp_file_path)

    title, text = content.split("# Content\n", 1)
    title = title.replace("# Title\n", "").strip()
    text = text.strip()

    output_dir = os.path.expanduser(f"~/Downloads/{title}")
    voice = "zh-CN-XiaoxiaoNeural"
    asyncio.run(generate_tts(text, voice, output_dir))