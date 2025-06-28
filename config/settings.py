import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Flask Configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'a_very_secret_key_that_should_be_changed')
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///local.db')

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Server Configuration
PORT = int(os.getenv('PORT', 5000))
DEBUG = os.environ.get('RENDER', '') != 'true'

# Render Configuration
IS_RENDER = os.environ.get("RENDER", "") == "true" 