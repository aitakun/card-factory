"""Authentication utilities for OnlyOffice API"""

import os
from dotenv import load_dotenv


def validate_api_key(api_key):
    """Validate that API key is present and properly formatted"""
    if not api_key:
        raise ValueError("API key is required")
    if not isinstance(api_key, str):
        raise ValueError("API key must be a string")
    if len(api_key.strip()) == 0:
        raise ValueError("API key cannot be empty")
    return api_key.strip()


def load_api_key_from_env():
    """Load API key from environment variables"""
    load_dotenv()  # Load environment variables from .env file
    api_key = os.getenv("ONLYOFFICE_API_KEY")
    if not api_key:
        raise ValueError("API key not found. Please set ONLYOFFICE_API_KEY in your .env file")
    return validate_api_key(api_key)