"""
ai.py - Natural language to SQL using Google Gemini REST API.
Uses requests instead of gRPC to avoid network blocking issues.
"""
import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

MODEL = "gemini-3.1-flash-lite"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"


def call_gemini(prompt):
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in .env file.")

    response = requests.post(
        f"{API_URL}?key={api_key}",
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=30
    )

    if response.status_code != 200:
        raise Exception(f"Gemini API error {response.status_code}: {response.text}")

    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def nl_to_sql(user_message, schema_str, history=None):
    history_text = ""
    if history:
        for msg in history[-6:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_text += f"{role}: {msg['content']}\n"

    prompt = f"""You are a SQLite SQL expert. Convert the user's request into a single valid SQLite SQL statement.

DATABASE SCHEMA:
{schema_str}

RULES:
- Return ONLY the raw SQL statement. No explanation. No markdown. No backticks.
- Use only table/column names from the schema above.
- Never use PRAGMA, ATTACH, DETACH, VACUUM, or transaction statements.
- Return exactly ONE SQL statement.
- If you cannot convert the request, reply with: ERROR: <reason>

{f"RECENT CONVERSATION:{chr(10)}{history_text}" if history_text else ""}

USER REQUEST: {user_message}

SQL:"""

    try:
        sql = clean_sql(call_gemini(prompt))
        if sql.upper().startswith("ERROR:"):
            return {"sql": None, "error": sql[6:].strip()}
        return {"sql": sql, "error": None}
    except Exception as e:
        return {"sql": None, "error": str(e)}


def fix_sql(bad_sql, error_msg, schema_str):
    prompt = f"""A SQL statement failed. Fix it.

SCHEMA:
{schema_str}

FAILED SQL: {bad_sql}
ERROR: {error_msg}

Return ONLY the corrected SQL, nothing else.

CORRECTED SQL:"""
    try:
        return {"sql": clean_sql(call_gemini(prompt)), "error": None}
    except Exception as e:
        return {"sql": None, "error": str(e)}


def clean_sql(text):
    text = re.sub(r"```(?:sql)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text)
    return text.strip()