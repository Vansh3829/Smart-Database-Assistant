"""
test.py - Test if Gemini API is working.
Run with: python3 test.py
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

print("=" * 50)
print("  Smart Database Assistant - API Test")
print("=" * 50)

# Check API key
api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    print("\n❌ GEMINI_API_KEY not found in .env file.")
    sys.exit(1)
print(f"\n✅ API Key found: {api_key[:8]}...{api_key[-4:]}")

# Test internet
print("\n⏳ Testing internet connection...")
try:
    r = requests.get("https://www.google.com", timeout=5)
    print("✅ Internet is working.")
except Exception:
    print("❌ No internet connection.")
    sys.exit(1)

# Test Gemini REST API
print("\n⏳ Testing Gemini API...")
MODEL = "gemini-3.1-flash-lite"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"

try:
    r = requests.post(URL, json={
        "contents": [{"parts": [{"text": "Reply with exactly: API is working!"}]}]
    }, timeout=15)

    if r.status_code == 200:
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        print(f"✅ Gemini responded: {text.strip()}")
        print("\n🎉 Everything is working! Run: python3 app.py")
    elif r.status_code == 403 or r.status_code == 401:
        print(f"❌ Invalid API key. Get a new one at: https://aistudio.google.com/app/apikey")
    elif r.status_code == 429:
        print(f"⚠️  Rate limit hit. Wait a few minutes and try again.")
    else:
        print(f"❌ Error {r.status_code}: {r.text[:200]}")

except requests.exceptions.ConnectionError:
    print("❌ Cannot reach Google's servers.")
    print("   Try: sudo networksetup -setdnsservers Wi-Fi 8.8.8.8 8.8.4.4")
    print("   Or switch to mobile hotspot.")
except requests.exceptions.Timeout:
    print("❌ Request timed out. Network is too slow or blocking Google.")