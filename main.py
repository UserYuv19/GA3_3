from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import sys
from io import StringIO
import traceback
import re

app = FastAPI()

# ✅ Enable CORS (required for testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================
# Request & Response Models
# ============================

class CodeRequest(BaseModel):
    code: str


class CodeResponse(BaseModel):
    error: List[int]
    result: str


# ============================
# TOOL FUNCTION
# Executes Python code safely
# ============================

def execute_python_code(code: str) -> dict:
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    # ⭐ Shared environment (fixes recursion & functions)
    env = {}

    try:
        exec(code, env, env)   # IMPORTANT FIX
        output = sys.stdout.getvalue()
        return {"success": True, "output": output}

    except Exception:
        output = traceback.format_exc()
        return {"success": False, "output": output}

    finally:
        sys.stdout = old_stdout


# ============================
# Extract Error Line Numbers
# From traceback (no AI needed)
# ============================

def extract_error_lines(traceback_text: str) -> List[int]:
    # Looks for: File "<string>", line X
    lines = re.findall(r'File "<string>", line (\d+)', traceback_text)
    return sorted(set(map(int, lines)))


# ============================
# ENDPOINT
# ============================

@app.post("/code-interpreter", response_model=CodeResponse)
async def code_interpreter(request: CodeRequest):

    result = execute_python_code(request.code)

    # ✅ Successful execution
    if result["success"]:
        return {
            "error": [],
            "result": result["output"]
        }

    # ❌ Error → extract line numbers
    error_lines = extract_error_lines(result["output"])

    return {
        "error": error_lines,
        "result": result["output"]
    }
