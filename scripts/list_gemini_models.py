#!/usr/bin/env python3
"""List available Gemini models."""

import os
import google.generativeai as genai

# Set your API key
api_key = os.getenv("GOOGLE_API_KEY", "AIzaSyCrr3bJZw837ppcRwuKhb7lIMptCFaG498")
genai.configure(api_key=api_key)

print("Available Gemini models:")
print("-" * 60)

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"✓ {model.name}")
        print(f"  Display name: {model.display_name}")
        print(f"  Description: {model.description[:100]}...")
        print()
