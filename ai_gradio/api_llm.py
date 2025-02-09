from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from enum import Enum
import re

# 環境変数の読み込み
load_dotenv()

# integrated_gradio から必要な関数と定数をインポート
from .integrated_gradio import generate_gemini, DEFAULT_TEXT_SYSTEM_PROMPT
from .logging_config import setup_logging  # ロガーをインポート

# ロガーの初期化
logger = setup_logging()

app = FastAPI()

# フォーマットタイプの列挙型
class FormatType(str, Enum):
    TEXT = "text"
    JSON = "json"

def remove_code_block(text):
    """コードブロックを除去する関数"""
    # ```json や ``` で囲まれたブロックから中身だけを抽出
    pattern = r'```(?:json)?\n?(.*?)\n?```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()

# リクエストボディ用の pydantic モデル
class LLMRequest(BaseModel):
    prompt: str
    format_type: FormatType = FormatType.TEXT  # デフォルトはテキストモード

# POST /api/llm エンドポイント
@app.post("/api/llm")
async def llm_api(request: LLMRequest):
    """
    リクエストの prompt を使って gemini-2.0-flash モデルで LLM 呼び出しを行います。
    format_type に応じてテキストまたはJSONで応答を返します。
    """
    logger.info(f"LLM API Request - Prompt: {request.prompt}, Format: {request.format_type}")
    
    try:
        default_model = "gemini-2.0-flash"
        response_text, _ = generate_gemini(
            request.prompt, 
            default_model, 
            DEFAULT_TEXT_SYSTEM_PROMPT, 
            "Text"
        )
        
        # コードブロックがある場合は除去
        response_text = remove_code_block(response_text)
        logger.info(f"LLM API Response: {response_text}")
        
        # format_type に応じて応答形式を変更
        if request.format_type == FormatType.JSON:
            try:
                # JSONモードの場合は、応答をJSONとしてパースして返す
                import json
                json_response = json.loads(response_text)
                return JSONResponse(content=json_response)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {str(e)}")
                return JSONResponse(
                    status_code=422,
                    content={"error": "Response could not be parsed as JSON"}
                )
        else:
            # テキストモードの場合は、そのまま平文で返す
            return PlainTextResponse(response_text)
            
    except Exception as e:
        logger.error(f"LLM API Error: {str(e)}")
        if request.format_type == FormatType.JSON:
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )
        raise 