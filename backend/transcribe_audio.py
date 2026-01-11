import requests
import os
from dotenv import load_dotenv
import json
import base64
from urllib.parse import urlparse
from pathlib import Path
from requests.auth import HTTPBasicAuth

load_dotenv()

def encode_audio_to_base64(file_path):
    """Encodes an audio file to a base64 string."""
    with open(file_path, 'rb') as audio_file:
        return base64.b64encode(audio_file.read()).decode('utf-8')
    
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

example_json = (Path(__file__).resolve().parent / "example.json").read_text(encoding="utf-8").strip()

def transcribe_url(src: str, call_start_time: str):
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    resp = requests.get(src, timeout=30, auth=HTTPBasicAuth(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
    resp.raise_for_status()
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    base64_audio = base64.b64encode(resp.content).decode('utf-8')
    example_json = (Path(__file__).resolve().parent / "example.json").read_text(encoding="utf-8").strip()
    messages = [{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Respond in a JSON format. Please transcribe this audio file. Every second, attach a timestamp in the format [mm:ss] before the corresponding text. Next, if you can determine the location from the caller's speech, create another object with key location and text that is the location or address, otherwise create that object but leave the value as empty. Here is a complete example: {example_json}. Also, add in the {call_start_time} as shown in the example. Do not say anything other than what is asked."
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
        "model": "google/gemini-3-pro-preview",
        "messages": messages
    }
    response = requests.post(url, headers=headers, json=payload)
    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content")
    print(content)
    return(content)


# NOTE: Leo I changed this to be a standalone script to test the transcribe_url function.
# If you need to test the transcribe_url function, you can run this script.
if __name__ == "__main__":
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


# NOTE: Leo I changed this to be a standalone script to test the transcribe_url function.
# If you need to test the transcribe_url function, you can run this script.
if __name__ == "__main__":
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