import requests
import os
from dotenv import load_dotenv
import json
import base64
from urllib.parse import urlparse
from pathlib import Path
from requests.auth import HTTPBasicAuth

def encode_audio_to_base64(file_path):
    """Encodes an audio file to a base64 string."""
    with open(file_path, 'rb') as audio_file:
        return base64.b64encode(audio_file.read()).decode('utf-8')
    
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

def transcribe_url(src: str):
    resp = requests.get(src, timeout=30, auth=HTTPBasicAuth(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
    resp.raise_for_status()
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    base64_audio = base64.b64encode(resp.content).decode('utf-8')
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
