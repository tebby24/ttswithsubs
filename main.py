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


def preprocess_text(input_text):
    """
    Preprocess the input text to normalize punctuation, collapse whitespace, and ensure consistency.
    """
    logger.debug("Original input text:")
    logger.debug(input_text)

    # 1. Normalize punctuation
    normalized_text = input_text
    normalized_text = normalized_text.replace("……", "...")  # Replace ellipsis
    normalized_text = normalized_text.replace("“", '"').replace("”", '"')  # Replace quotes
    normalized_text = normalized_text.replace("‘", "'").replace("’", "'")  # Replace single quotes

    # 2. Collapse whitespace and remove unnecessary characters
    normalized_text = re.sub(r'\s+', ' ', normalized_text)  # Replace multiple spaces/newlines with single space
    normalized_text = normalized_text.strip()  # Trim leading/trailing spaces

    # 3. Remove unsupported symbols (optional)
    # Define valid Mandarin characters (including basic CJK Unicode range)
    valid_characters = re.compile(r'[。，！？；：“”（）《》〈〉、…\w\s]')
    normalized_text = ''.join(char for char in normalized_text if valid_characters.match(char))

    # 4. Space around punctuation (optional, if alignment benefits from this)
    # E.g., "毛泽东，中华人民共和国。" -> "毛泽东 ， 中华人民共和国 。"
    spaced_text = re.sub(r'(。|，|！|？|；)', r' \1 ', normalized_text)
    spaced_text = re.sub(r'\s+', ' ', spaced_text)  # Remove extra spaces created by spacing adjustment

    logger.debug("Preprocessed text:")
    logger.debug(spaced_text)

    return spaced_text


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
        # Preprocess chunk to remove punctuation for word-level matching
        clean_chunk = re.sub(r'[，。？！？；：、“”‘’（）【】《》〈〉、……]', '', chunk)

        # Handle punctuation-only chunks
        if not clean_chunk:
            logger.debug(f"Skipping punctuation-only chunk: '{chunk}'")
            # Add the punctuation-only chunk to the result without timestamps
            result.append((chunk, None, None))
            continue

        # Match words in the chunk to SRT entries
        words_matched = []
        start_time = None
        end_time = None
        while current_word_index < entry_count and clean_chunk:
            srt_word = srt_entries[current_word_index].content

            if clean_chunk.startswith(srt_word):
                if not start_time:  # Set the first matched word's start time
                    start_time = srt_entries[current_word_index].start

                clean_chunk = clean_chunk[len(srt_word):]  # Remove matched part
                words_matched.append(srt_word)
                end_time = srt_entries[current_word_index].end  # Update end time
                current_word_index += 1  # Move to the next word entry
            else:
                break
        
        # Ensure all words in the chunk are matched
        if words_matched and start_time is not None and end_time is not None:
            result.append((chunk, start_time, end_time))
            logger.debug(f"Chunk '{chunk}' aligned to start: {start_time}, end: {end_time}")
        else:
            logger.error(f"Failed to match chunk: '{chunk}'. Remaining clean chunk: '{clean_chunk}'. Start index: {current_word_index}")
            raise ValueError(f"Unable to fully match the chunk '{chunk}' with word SRT entries.")
    
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
        if start_time is None or end_time is None:
            # Skip punctuation-only chunks with no timestamps
            logger.debug(f"Skipping punctuation-only subtitle entry: '{chunk}'")
            continue

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
    processed_text = preprocess_text(text)
    logger.debug(f"Preprocessed TEXT: {processed_text}")

    output_dir = os.path.expanduser(f"~/Downloads/{title}")
    voice = "zh-CN-XiaoxiaoNeural"
    asyncio.run(generate_tts(processed_text, voice, output_dir))