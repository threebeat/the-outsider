#!/usr/bin/env python3
"""
Simple test script to verify OpenAI API key configuration.
Run this locally or on Render to test if the API key is working.
"""

import os
from openai import OpenAI

def test_openai_connection():
    """Test OpenAI API connection and key validity."""
    print("=== OpenAI API Key Test ===")
    
    # Check if we're on Render
    is_render = os.environ.get("RENDER") == "true"
    print(f"Environment: {'Render' if is_render else 'Local'}")
    
    # Get API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY environment variable is not set!")
        return False
    
    print(f"✅ API Key found: {api_key[:7]}...")
    
    # Test the API key
    try:
        client = OpenAI(api_key=api_key, timeout=20.0)
        
        # Make a simple test request
        print("🔄 Testing API connection...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Say 'Hello, API test successful!'"}],
            max_tokens=10,
            timeout=10
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ API Test Successful! Response: {result}")
        return True
        
    except Exception as e:
        print(f"❌ API Test Failed: {e}")
        return False

if __name__ == "__main__":
    success = test_openai_connection()
    if success:
        print("\n🎉 OpenAI API is working correctly!")
    else:
        print("\n💥 OpenAI API test failed. Check your configuration.") 