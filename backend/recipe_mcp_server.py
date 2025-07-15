"""
MCP-compliant AI Model Server (FastAPI)
- Exposes /v1/completions endpoint
- Forwards prompt to Google Gemini via google.generativeai
- Returns response in MCP format
"""

import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai
import logging

# Load environment variables (for GEMINI_API_KEY)
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("recipe_mcp_server")

app = FastAPI(title="MCP-compliant AI Model Server")

# Request schema for /v1/completions
class CompletionRequest(BaseModel):
    model: str
    prompt: str
    parameters: dict = {}

# Response schema for MCP
class Choice(BaseModel):
    text: str
    index: int = 0

class CompletionResponse(BaseModel):
    id: str
    object: str = "text_completion"
    model: str
    choices: list

# Helper to get Gemini model

def get_gemini_model(model_name: str):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set in environment.")
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)

@app.post("/v1/completions", response_model=CompletionResponse)
async def completions(request: CompletionRequest):
    """
    MCP-compliant endpoint for text completions.
    """
    try:
        model = get_gemini_model(request.model)
        # Only 'prompt' and 'max_tokens' supported for simplicity
        prompt = request.prompt
        max_tokens = request.parameters.get("max_tokens", 512)
        # Gemini API does not use max_tokens directly, but you can pass it if needed
        response = model.generate_content(prompt)
        text = response.text
        return CompletionResponse(
            id="completion-1",
            model=request.model,
            choices=[Choice(text=text, index=0).dict()]
        )
    except Exception as e:
        logger.error(f"Completion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "MCP-compliant AI Model Server running."}
