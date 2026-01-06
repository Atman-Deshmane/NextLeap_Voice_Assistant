"""
Groq Voice Service for Speech-to-Text and Text-to-Speech.
Uses Whisper for transcription and Orpheus for speech synthesis.
"""

import os
import base64
from typing import Optional
from groq import Groq

# Initialize Groq client
_client = None

def _get_client():
    """Get or create Groq client."""
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        _client = Groq(api_key=api_key)
    return _client


def transcribe_audio(audio_file_object) -> str:
    """
    Transcribe audio to text using Whisper.
    
    Args:
        audio_file_object: File-like object containing audio data (Flask FileStorage)
        
    Returns:
        Transcribed text string
    """
    client = _get_client()
    
    try:
        # Read file content and create tuple format expected by Groq
        # Format: (filename, file_content, content_type)
        file_content = audio_file_object.read()
        filename = getattr(audio_file_object, 'filename', 'audio.webm')
        
        transcription = client.audio.transcriptions.create(
            file=(filename, file_content),
            model="whisper-large-v3-turbo"
        )
        
        transcript = transcription.text
        print(f"🎤 Transcribed: {transcript}")
        return transcript
        
    except Exception as e:
        print(f"❌ STT Error: {e}")
        raise


def clean_text_for_speech(text: str) -> str:
    """
    Clean text for natural speech by removing markdown formatting.
    
    Args:
        text: Raw text with potential markdown
        
    Returns:
        Clean text suitable for TTS
    """
    import re
    
    # Remove markdown formatting characters
    cleaned = re.sub(r'[*#_`]', '', text)
    
    # Remove markdown links [text](url) -> text
    cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned)
    
    # Remove standalone URLs
    cleaned = re.sub(r'https?://\S+', '', cleaned)
    
    # Remove bullet points
    cleaned = re.sub(r'^[\s]*[-•]\s*', '', cleaned, flags=re.MULTILINE)
    
    # Collapse multiple spaces/newlines
    cleaned = re.sub(r'\n+', '. ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    return cleaned.strip()


def generate_audio(text: str) -> Optional[bytes]:
    """
    Generate speech audio from text using Orpheus TTS.
    
    Args:
        text: Text to convert to speech
        
    Returns:
        Audio bytes (WAV format), or None if TTS fails (rate limit, etc.)
    """
    client = _get_client()
    
    # Clean markdown for natural speech
    clean_text = clean_text_for_speech(text)
    
    try:
        response = client.audio.speech.create(
            model="canopylabs/orpheus-v1-english",
            input=clean_text,
            voice="hannah",
            response_format="wav"
        )
        
        # Get audio bytes from response
        audio_bytes = response.read()
        print(f"🔊 TTS Generated: {len(audio_bytes)} bytes")
    except Exception as e:
        # Don't crash on TTS failure (rate limit, etc.)
        err_msg = str(e)
        print(f"⚠️ TTS Failed: {err_msg}")
        return None, err_msg
    
    return audio_bytes, None


def audio_to_base64(audio_bytes: bytes) -> str:
    """
    Encode audio bytes to base64 string for JSON response.
    
    Args:
        audio_bytes: Raw audio bytes
        
    Returns:
        Base64 encoded string
    """
    return base64.b64encode(audio_bytes).decode('utf-8')
