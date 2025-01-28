from moviepy import *
# Import the audio(Insert to location of your audio instead of audioClip.mp3)
audio = AudioFileClip("test/speech.mp3")
# Import the Image and set its duration same as the audio (Insert the location 
clip = ImageClip("test/Mao_Proclaiming_New_China.jpeg").with_duration(audio.duration)
# Set the audio of the clip
clip = clip.with_audio(audio)
# Export the clip
clip.write_videofile("test/video.mp4", fps=24)