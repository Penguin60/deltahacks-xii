import requests
import os
from dotenv import load_dotenv
import json
import base64

def encode_audio_to_base64(file_path):
    """Encodes an audio file to a base64 string."""
    with open(file_path, 'rb') as audio_file:
        return base64.b64encode(audio_file.read()).decode('utf-8')

load_dotenv()

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
    "Content-Type": "application/json"
}

# Read and encode the audio file

audio_path = "transcribe_test.wav"

base64_audio = encode_audio_to_base64(audio_path)

messages = [{
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Please transcribe this audio file."
            },
            {
                "type": "input_audio",
                "input_audio": {
                    "data": base64_audio,
                    "format": "wav"
                }
            }
        ]
}]
payload = {
    "model": "mistralai/voxtral-small-24b-2507",
    "messages": messages
}
response = requests.post(url, headers=headers, json=payload)

print(response.json())
