from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# integrated_gradio から必要な関数と定数をインポート
from .integrated_gradio import generate_gemini, DEFAULT_TEXT_SYSTEM_PROMPT

app = FastAPI()

# リクエストボディ用の pydantic モデル
class LLMRequest(BaseModel):
    prompt: str

# POST /api/llm エンドポイント
@app.post("/api/llm", response_class=PlainTextResponse)
async def llm_api(request: LLMRequest):
    """
    リクエストの prompt を使って gemini-2.0-flash モデルで LLM 呼び出しを行い、
    結果のテキストをそのまま返します。
    """
    default_model = "gemini-2.0-flash"
    # prompt_type は "Text" を指定して、シンプルなテキスト応答とする
    response_text, _ = generate_gemini(request.prompt, default_model, DEFAULT_TEXT_SYSTEM_PROMPT, "Text")
    return response_text 