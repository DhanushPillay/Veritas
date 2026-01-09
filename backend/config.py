"""
VERITAS - Configuration
Loads environment variables and settings
"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Config:
    """Application configuration"""
    
    # API Keys
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')
    TINEYE_API_KEY = os.environ.get('TINEYE_API_KEY', '')
    NEWS_API_KEY = os.environ.get('NEWS_API_KEY', '')
    
    # Server settings
    HOST = '127.0.0.1'
    PORT = 5000
    DEBUG = True
    
    # AI Models
    TEXT_MODEL = 'meta-llama/llama-4-scout-17b-16e-instruct'
    AUDIO_MODEL = 'whisper-large-v3-turbo'
    
    @classmethod
    def validate(cls):
        """Validate required settings"""
        if not cls.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set in .env file")
        return True
