from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import sys
from io import StringIO
import traceback
import requests
import json

app = FastAPI()

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔐 AI PIPE TOKEN
AIPIPE_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIyZjMwMDI5ODdAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9.0ByYJrCcZMkknLE0YWztzn37XUbr3Q5OKu_4P_EM4jQ"


# ============================
# MODELS
# ============================

class CodeRequest(BaseModel):
    code: str


class CodeResponse(BaseModel):
    error: List[int]
    result: str


# ============================
# TOOL FUNCTION
# ============================

def execute_python_code(code: str) -> dict:
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        exec(code)
        output = sys.stdout.getvalue()
        return {"success": True, "output": output}

    except Exception:
        output = traceback.format_exc()
        return {"success": False, "output": output}

    finally:
        sys.stdout = old_stdout


# ============================
# AI ERROR ANALYSIS USING AI PIPE
# ============================

def analyze_error_with_ai(code: str, tb: str) -> List[int]:
    url = "https://aipipe.org/openrouter/v1/responses"

    prompt = f"""
Analyze this Python code and traceback.
Return ONLY JSON:

{{ "error_lines": [line_numbers] }}

CODE:
{code}

TRACEBACK:
{tb}
"""

    payload = {
        "model": "openai/gpt-4.1-mini",
        "input": prompt
    }

    headers = {
        "Authorization": f"Bearer {AIPIPE_TOKEN}",
        "Content-Type": "application/json"
    }

    r = requests.post(url, headers=headers, json=payload, timeout=30)

    if r.status_code != 200:
        return []

    data = r.json()

    # Extract text from AI Pipe response
    try:
        for item in data.get("output", []):
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    text = c.get("text")
                    return json.loads(text).get("error_lines", [])
    except:
        pass

    return []


# ============================
# ENDPOINT
# ============================

@app.post("/code-interpreter", response_model=CodeResponse)
async def code_interpreter(request: CodeRequest):

    result = execute_python_code(request.code)

    # ✅ Success
    if result["success"]:
        return {
            "error": [],
            "result": result["output"]
        }

    # ❌ Error → AI analyzes
    error_lines = analyze_error_with_ai(
        request.code,
        result["output"]
    )

    return {
        "error": error_lines,
        "result": result["output"]
    }