# Text-to-Speech with Subtitles

This project synthesizes text to speech with a matching subtitle file using the Microsoft Azure text to speech API. You'll need to get your own API key. 

## Installation

1. Clone the repository and navigate into it:
    ```sh
    git clone <repository-url>
    cd ttswithsubs_dev
    ```

2. Create a virtual Python environment:
    ```sh
    python -m venv venv
    source venv/bin/activate
    ```

3. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

## Usage

1. Set up your environment variables in a .env file:
    ```env
    AZURE_SPEECH_KEY=your_azure_speech_key
    AZURE_SPEECH_REGION=your_azure_speech_region
    ```

2. Run the cli:
    ```sh
    python cli.py
    ```

Follow the instructions