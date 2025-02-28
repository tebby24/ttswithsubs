import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'modules')))

from video import generate_video

if __name__ == "__main__":
    generate_video(
        "bin/test/input/test_image.jpeg", 
        "bin/test/input/test_mp3.mp3",
        "bin/test/output/mp4_test.mp4"
    )