#!/bin/bash
# Test Gemini API with curl

API_KEY="${GOOGLE_API_KEY:-AIzaSyCrr3bJZw837ppcRwuKhb7lIMptCFaG498}"

echo "Testing Gemini API..."
echo "API Key: ${API_KEY:0:20}..."
echo ""

# Test with gemini-1.5-flash
curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${API_KEY}" \
  -H 'Content-Type: application/json' \
  -d '{
    "contents": [{
      "parts": [{
        "text": "Say hello"
      }]
    }]
  }' | jq '.'

echo ""
echo "---"
echo ""

# List available models
echo "Available models:"
curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=${API_KEY}" | jq -r '.models[] | select(.supportedGenerationMethods[] | contains("generateContent")) | .name'
