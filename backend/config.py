import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    """Application configuration"""
    
    # API Keys
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
    
    # Server settings
    HOST = '127.0.0.1'
    PORT = 5000
    DEBUG = True
    
    # AI Model
    MODEL = 'meta-llama/llama-4-scout-17b-16e-instruct'
    
    # System prompt for the chatbot
    SYSTEM_PROMPT = """You are Veritas, a helpful and friendly AI assistant. 
You provide clear, accurate, and thoughtful responses.
You can help with coding, writing, analysis, math, and general questions.
Be concise but thorough. Use markdown formatting when helpful."""
    
    @classmethod
    def validate(cls):
        """Validate required settings"""
        if not cls.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set in .env file")
        return True
