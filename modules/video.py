from moviepy import *

def generate_video(image_filepath, mp3_filepath, mp4_output_dir):
    audio = AudioFileClip(mp3_filepath)
    clip = ImageClip(image_filepath).with_duration(audio.duration)
    clip = clip.with_audio(audio)
    clip.write_videofile(mp4_output_dir, fps=24)

