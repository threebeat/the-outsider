import os
from dotenv import load_dotenv

# Only load the .env file if we're not on Render (i.e., we are in a local environment)
if os.environ.get("RENDER") != "true":
    load_dotenv()

# Flask Configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'a_very_secret_key_that_should_be_changed')
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///local.db')

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Debug environment variable loading
if os.environ.get("RENDER") == "true":
    print(f"Running on Render - RENDER env var: {os.environ.get('RENDER')}")
    print(f"OPENAI_API_KEY present: {'Yes' if OPENAI_API_KEY else 'No'}")
    if OPENAI_API_KEY:
        print(f"OPENAI_API_KEY starts with: {OPENAI_API_KEY[:7]}...")
else:
    print(f"Running locally - RENDER env var: {os.environ.get('RENDER')}")
    print(f"OPENAI_API_KEY present: {'Yes' if OPENAI_API_KEY else 'No'}")

# Server Configuration
PORT = int(os.getenv('PORT', 5000))
DEBUG = os.environ.get('RENDER', '') != 'true'

# Render Configuration
IS_RENDER = os.environ.get("RENDER", "") == "true" 