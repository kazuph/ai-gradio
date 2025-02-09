import uvicorn
from .integrated_gradio import build_interface
from .api_llm import app as fastapi_app
import gradio as gr
from fastapi.middleware.cors import CORSMiddleware

def create_app():
    # FastAPI アプリケーションの設定
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 本番環境では適切に制限してください
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Gradio インターフェースの作成
    demo = build_interface()
    
    # GradioアプリをFastAPIにマウント
    app = gr.mount_gradio_app(fastapi_app, demo, path="/")
    
    return fastapi_app

def main():
    # アプリケーションの作成
    app = create_app()
    
    # サーバーの起動
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=7860,
        log_level="info"
    )

if __name__ == "__main__":
    main() 